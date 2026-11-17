# HOST de BMO-X2

La sesion visual C++ se construye y prueba en `tools/desktop/rmlui/`.
Su productor HOST empaqueta RML/RCSS, fuentes, UJBC y DLL con hashes;
entrega recursos en memoria al contrato `bmo-ui-memory-v1`. No usa
`pack` como si una DLL Windows fuera SBEF: el lector mantiene su rechazo.
La auditoria separa el objeto del adaptador sin llamadas Kernel32
directas del runtime/STL/FreeType que aun requieren adaptacion.
Ver [sesion, animacion y limites](../desktop/rmlui/README.md).

HOST recibe un ejecutable x86-64 enlazado y decide si cumple el perfil
de aplicacion. El resultado admitido es un SBEF con un ABI, entrada,
regiones y permisos definidos. El ejecutable mantiene el codigo de
maquina que emitio el compilador.

## Frontera con el NANO-CORE

HOST trabaja para el destino x86-64 y fuera del Ring 0 de BMO-X2.
Los importadores, compiladores, resolucion de dependencias y politicas
de construccion pertenecen a herramientas o servicios sin autoridad
privilegiada sobre el sistema invitado. El NANO-CORE conserva la decision
de admitir la imagen y conceder capacidades. Su cargador valida SBEF
de nuevo; un informe favorable de HOST no sustituye esa comprobacion.

La portabilidad entre CPUs no es requisito del proyecto. Una variante
de otra arquitectura tendria herramientas y backend propios en otro
proyecto. La especializacion permite preparar el resultado para un
destino definido, con medidas de tamano, memoria y ejecucion.

La implementacion actual valida perfiles concretos y empaqueta codigo
nativo ya enlazado. El backend propio total, la adaptacion general de
dependencias de otros sistemas, la ejecucion de HOST dentro del Ring 3
de BMO-X2 y el aislamiento de importadores aun estan pendientes. Cuando
se amplie un productor, debe declarar entradas, salida, diagnosticos,
limites de recursos, pruebas de rechazo y evidencia de ejecucion.

| Carpeta o archivo | Responsabilidad |
|---|---|
| `toolchains/abi.py` | Coordinar el banco ABI y cotejar el portal SysV con su vector HEX. |
| `toolchains/msvc.py` | Compilar COFF con MSVC, enlazar el portal Rust Win64 y preparar el cliente PE para el banco. |
| `importers/elf.py` | Validar ELF64 estatico y extraer los segmentos cargables. |
| `importers/pe.py` | Inventariar PE32+, validar perfiles fijos RX o RX/R/RW y explicar rechazos. |
| `importers/pe_imports.py` | Censar DLL, simbolos y ordinales de importaciones normales, con limites de lectura. |
| `importers/pe_bindings.py` | Resolver las importaciones del catalogo del banco MSVC, en la IAT de solo lectura del SBEF. |
| `sbef/format.py` | Definir y validar cabecera, tabla, rangos, permisos y entrada SBEF. |
| `diagnostics.py` | Identificar cada rechazo por codigo, campo, offset e indice cuando aplica. |
| `cli.py` | Leer entradas acotadas y publicar el SBEF solo tras validarlo. |

Los comandos siguen entrando por `tools/sbef.py` y
`tools/abi_toolchain.py`. El [contrato SBEF](../../contracts/SBEF-HOST.md)
describe las opciones. El [ABI](../../contracts/ABI.md) define las
peticiones a Ring 0 y el [cargador](../../contracts/SBEF-LOADER.md)
vuelve a validar el archivo que recibe.

## Banco x86-64

Con `--abi-run`, el banco construye un cliente freestanding, genera
SBEF ABI 1 y lo ejecuta en la sonda CASM de QEMU. Se comprueban
INVOKE, el rechazo de capacidad, WAIT y el borrado de codigo y pila
tras un fallo controlado desde CPL3. `--language cpp` usa el mismo
cliente fuente y `--language rust` usa rustc con el mismo portal ABI.
Cada run guarda la huella de su SBEF y el informe de QEMU.

El reto de 2 KiB exige que `INICIO.X86` contenga en 2048 bytes o menos
la cabecera, la sonda CASM Ring 0 y el cliente SBEF Ring 3. El banco
rechaza un exceso antes de construir la imagen y registra el desglose,
el margen y el total junto con el puente EFI. El primer perfil usa un
cliente y tres llamadas de prueba. El puente UEFI, las tablas, la pila
en RAM, los controladores y el escritorio tienen presupuestos propios.
El comando `pack` admite limites opcionales de archivo y paginas
mapeadas para que cada aplicacion declare su propio presupuesto.

El banco embebe una region RX por cliente. Con `--reuse --abi-run`
ejecuta dos SBEF distintos en las mismas dos paginas de usuario. La
sonda verifica que el codigo y la pila anteriores quedaron desmapeados
y a cero antes de volver a usarlos. El paquete con Clang pesa 1980 bytes.
La etapa de reuso es una extension ensamblada de la sonda CASM. Faltan
el cargador externo general, los propietarios de proceso y la
revocacion de capacidades por proceso.
En la consola x64 de Visual Studio, `python -B tools/abi_toolchain.py
msvc --pe-link link.exe` compila C a COFF, enlaza el portal Rust
`extern "win64"` y entrega un PE32+ x86-64 de inspeccion sin CRT,
DLL importadas ni TLS. El portal traduce los argumentos y el retorno
de Microsoft x64 al contrato INVOKE/WAIT de BMO-X2.

Para recorrer la ruta completa desde la consola x64 de Visual Studio,
con Clang y el target Rust `x86_64-pc-windows-msvc`:

```powershell
python -B tools/abi_toolchain.py msvc --pe-link link.exe --abi-run build/CASM/run-20261112-174958-944cb997
```

El perfil de la sonda enlaza una region RX en `0x40000000`, con entrada
Win64 y metadatos inertes comprobados. HOST extrae el contenido virtual
y descarta cabeceras y relleno de archivo. El directorio de excepciones
admite registros de version 1 sin manejadores ni cadenas. El perfil
rechaza DLL, importaciones, relocaciones, TLS, regiones RW y directorios
fuera de su contrato. Win32 y DirectX requieren servicios propios
en Ring 3. [Evidencia QEMU](../../Reports/abi-msvc-qemu.json).

`--msvc-sections` junto a `--pe-link` y `--abi-run` prueba un segundo
perfil. HOST conserva `.text`, `.rdata` y `.data` con permisos RX,
R y RW. El cargador existente comprueba los permisos y pone a cero
el resto de `.data`. MSVC compila C++17 y `kernel32.lib` del SDK
genera importaciones de `GetTickCount64`, `GetStdHandle` y `WriteFile`.
HOST comprueba la IAT y enlaza los tres servicios Rust del mapa del
enlace antes de emitir el SBEF. El reloj lee los ticks PIT de la sesion
QEMU. La consola admite stdout sincronico por puerto serie.
La prueba confirma el saludo, los bytes escritos, el avance despues de
WAIT y el rechazo de W+X. [Evidencia](../../Reports/abi-msvc-hello-qemu.json).

Con `--msvc-sections --msvc-window` el mismo cliente dibuja un panel y un
triangulo por CPU. El modelo Rust de DIRECTOR compone el panel en una
superficie de 320x200 y la presenta mediante GOP. Super+Q retira el panel
y F1 lo reabre. El banco coteja los tres cuadros en QEMU, incluido el
fondo restaurado. El perfil visual usa `/Od` por el limite de metadatos
unwind encadenados. Sigue pendiente integrar el cliente en la sesion
RmlUi de escritorio y anadir las llamadas DXGI/Direct3D.
[Captura](../../Reports/abi-msvc-director.png) y
[evidencia](../../Reports/abi-msvc-director-qemu.json).

## Referencia de BMO-X para compatibilidad y graficos

Revision leida del padre: `6076bdefe`. Sus rutas se indican desde la
raiz de BMO-X.

| Componente del padre | Responsabilidad que sirve de referencia |
|---|---|
| `platform/shared/proton-x` | Inspeccion PE32+, reservas, relocaciones e importaciones. El cliente de Ring 3 aporta la memoria y el salto a la entrada. |
| `platform/shared/proton-x-casa` | Exportaciones Win64, incluidas Win32, DXGI y D3D12. Su interfaz `Plataforma` conecta las funciones con reloj, archivos, memoria, ventanas y dibujo. |
| `platform/shared/prometeo` y `platform/shared/verrano-trama` | Representacion de programas graficos, interpretacion y raster por CPU. |
| `platform/shared/verrano/src/dibujo.rs` | Contrato `DrawBackend` y comprobaciones compartidas para los ejecutores. |
| `platform/shared/proton-x-sm86` | Emisor SASS para SM86 y simulador para el banco HOST. La ejecucion en la RTX se verifica por separado. |
| `Ultra_userspace/apps/proton-x` | Carga, resuelve servicios y conecta la presentacion con DIRECTOR. Su censo informa dependencias antes de arrancar el programa. |

El parte `docs/metal/METAL_2026-10-13.md`, seccion 5, registra la intro
de Cyberpunk 2077 a 1280x720 por CPU, alrededor de 16 s por fotograma.
En la corrida medida la RTX dibujo cero lotes del juego. El camino
observado uso las funciones D3D12 de PROTON-X y el dibujo de la casa.
Vulkan figura como otra API posible sobre un backend y tiene su propio
plan en `platform/drivers/gpu/rdna4/PLAN_VULKAN.md`.

La primera adaptacion para BMO-X2 es el censo previo del padre.
`tools/sbef.py probe` muestra las importaciones normales, por DLL y
simbolo u ordinal, aunque el empaquetado quede rechazado. Un censo
invalido se informa por separado con el campo y offset. Se verifico con
un PE enlazado por MSVC que importa `KERNEL32.dll!GetTickCount64` y con
la regresion QEMU del cliente freestanding. No carga DLL ni ejecuta sus
funciones. Las importaciones diferidas conservan su diagnostico propio.

El siguiente ensayo debe ampliar la tabla de servicios y comprobar
que cada importacion admitida conserva su semantica. El paso grafico
siguiente es un ejemplo
pequeno con DXGI/D3D12, un ejecutor CPU y una superficie de DIRECTOR.
Para darlo por valido en QEMU se comprueba el cuadro y la finalizacion
de la cola. Vulkan y el emisor SM86 tienen pruebas propias de backend.
