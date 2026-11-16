# Candidato de escritorio RmlUi desde FAT32

El candidato une el motor RmlUi/FreeType, el dibujo Rust y la politica
DIRECTOR existente de Rust. Es un panel ULTRA-J con espacios y cierre,
no la migracion completa de CABINA, DOOM y todas las aplicaciones.
El arranque anterior se conserva para esas funciones.

## Que esta comprobado

- QEMU arranca el gato compacto CASM y lee el SBEF desde FAT32 mediante
  UEFI. No se inyecta un modulo con `-device loader`.
- Antes de ExitBootServices se reserva el rango privado de usuario de
  16 MiB en 04000000h, con propiedad registrada. El cargador comprueba
  esa reserva y el mapa antes de escribir alli; no usa RAM supuesta libre.
- El lector tiene un perfil explicito de hasta 2 MiB. El limite de
  16,512 bytes del escritorio anterior no se amplia silenciosamente.
- El archivo INICIO.X86 sigue cabiendo en la pagina de 4 KiB. Se utiliza
  el gato compacto, porque el HD y esta entrada excederian ese limite.
- DIRECTOR decide foco, espacios, movimiento y cierre. La superficie
  1x1 que usa su adaptador es solo un marcador de politica: no comparte
  como referencia Rust el framebuffer mutable propiedad de C++.
- El presentador acepta la superficie logica 1280x800. En GOP menores
  usa una vista 640x400; en los mayores usa escala entera y centrado.
  QEMU verifica los pixeles del camino normal y del GOP 1024x768.
- Se prueban Enter, clic PS/2, espacios, cierre, reapertura y rechazo
  W+X antes de copiar codigo. Se vuelve a leer el BOOTLOG de la imagen
  FAT32 y se compara el SBEF del disco con el ejecutable esperado.

El heap sigue acotado a 4 MiB y el framebuffer ocupa 4,096,000 bytes.
El candidato mide 1,845,846 bytes de SBEF; el pico medido de su heap es
3,050,544 bytes. Las pruebas y huellas quedan conservadas en
[la evidencia del candidato](../Ultra-J/evidence/rmlui-desktop-fat32.json).
El mapeo privado de 16 MiB incluye la pila. No equivale al peso total
del nano-core ni demuestra que todo BMO-X2 consuma 2 KiB.

## Prueba fisica preparada

En esta maquina ya se registro una entrada separada del firmware llamada
**BMO-X2 Desktop (RmlUi)**. Elegir ese nombre en el menu de arranque.
Tras la confirmacion de METAL del propietario se retiro la entrada
antigua **BMO-X2** del firmware. Sus cuatro archivos se archivaron con
SHA256 en `build/archives/retired-bmo-x2` y se retiraron de A: por pedido
del propietario. Linux/ULTRA y los otros arranques quedan fuera de esa limpieza.
Los archivos visibles en el Explorador no son entradas del menu UEFI.

En el volumen FAT32 BMO (A: bajo Windows), abrir desde el selector de
archivos del firmware UEFI:

```text
\EFI\BMO-X2\DESKTOP.EFI
```

El programa lee exclusivamente:

```text
\BMO-X2\DESKTOP\INICIO.X86
\BMO-X2\DESKTOP\DESKTOP.SBF
```

El despliegue del candidato nuevo no cambia
NVRAM, orden de arranque, particiones ni el cargador de Windows.
`DEPLOY.JSON` identifica los hashes copiados y los originales conservados.

La distribucion activa queda asi; las actualizaciones sobreescriben estas
mismas rutas y los respaldos van al proyecto:

```text
A:/EFI/BMO-X2/DESKTOP.EFI
A:/BMO-X2/DESKTOP/INICIO.X86
A:/BMO-X2/DESKTOP/DESKTOP.SBF
A:/BMO-X2/DESKTOP/DEPLOY.JSON
A:/BMO-X2/DESKTOP/BOOTLOG.TXT
```

`native/retire-legacy.ps1` solo retira los cuatro archivos exactos del
perfil anterior, tras comprobar la entrada nueva y todas sus huellas.
Archiva y verifica todos los originales antes de borrar el primero.
No hace una limpieza general de EFI ni usa borrados recursivos.

El registro opcional se hace por separado con
`tools/desktop/rmlui/native/register-desktop.ps1`, en PowerShell elevado.
Comprueba los tres hashes del candidato, reutiliza una entrada compatible
o crea una nueva al final de la lista. No selecciona el siguiente arranque
ni reinicia. Su recibo queda en `build/rmlui-native/firmware-desktop.json`.

El firmware debe ejecutar el EFI x86-64 propio; el procedimiento no cambia
la politica de Secure Boot. Si el firmware no ofrece abrir archivos,
hay que usar su selector/shell o preparar una entrada separada.

### Controles del candidato

| Entrada | Resultado |
| --- | --- |
| Ctrl+Super+1..4 | Cambiar espacio |
| Super+1..9 | Enfocar el numero de ventana dentro del espacio |
| Super+Shift+1..4 | Mover el panel al espacio elegido |
| Super+Q | Cerrar el panel enfocado; la base permanece |
| F1 o Abrir ULTRA-J | Abrir o traer el panel al espacio actual |
| Enter o boton Activar ULTRA-J | Ejecutar UJBC nativo si el panel esta activo |

Cerrar el panel retira su identidad de DIRECTOR; la base conserva el
documento/atlas para reabrirlo. No es todavia descarga completa de un
proceso SBEF ni liberacion del mapeo de usuario.

## Evidencia y limites en metal

El 16-11-2026 el propietario confirmo la presentacion de RmlUi en METAL
con fotografia y BOOTLOG PRE-EBS, GOP 1920x1080. Ver
[evidencia del arranque fisico](../Reports/rmlui-desktop-metal-20261116.json).
Esto acredita lectura UEFI y llegada visual a Ring 3, no entrada USB.

USB HID sigue pendiente: la ruta AMD existente lee descriptores, pero
faltan configuracion de interfaces/endpoints interrupt y entrega de
informes de teclado y raton. El candidato usa entrada PS/2; que funcione
en QEMU no acredita esos USB fisicos. La luz RGB tampoco acredita HID.

El candidato escribe, antes de salir de UEFI:

```text
A:\BMO-X2\DESKTOP\BOOTLOG.TXT
```

El encabezado es `BMO-X2 DESKTOP UEFI PRE-EBS`. Incluye tamano SBEF,
GOP_WIDTH/GOP_HEIGHT, CPUID, PS2 y controladores PCI xHCI. Es evidencia
de lectura/preparacion UEFI, no un registro en vivo de Ring 0/Ring 3.
Cada candidato nuevo sigue necesitando su propio archivo y fotografia
del escritorio o del error para acreditar el arranque fisico.

La nueva variante de presentacion deja el gato CASM como saludo visual,
sin el texto de exito METAL64/BootServices ni el mensaje de carga UEFI.
Se preservan las firmas internas del contexto, las rutas de error y los
diagnosticos de BOOTLOG; el nombre visible no cambia el contrato binario.

CHKDSK A: en solo lectura no encontro problemas. Eso comprueba la
estructura del FAT32 montado; no es un ensayo de superficie con /R,
ni una prueba de los drivers del sistema propio.

## Reproducir y copiar

Desde la raiz del proyecto, con los runs CASM verificados del ABI y del
gato compacto:

```powershell
python .\tools\desktop\rmlui\native\guest.py --desktop
python .\tools\desktop\rmlui\native\media.py <ABI_RUN> <GATO_COMPACTO_RUN>
python .\tools\desktop\rmlui\native\media.py <ABI_RUN> <GATO_COMPACTO_RUN> --low-gop
powershell.exe -NoProfile -ExecutionPolicy Bypass -File .\tools\boot\view.ps1 -Profile rmlui-desktop
```

Para copiar un run aprobado: `native/deploy.ps1 -Run <RUN> -Volume A:\`.
La herramienta valida el FAT32 existente, las pruebas y cada hash; omite
archivos identicos, copia solo el candidato y respalda la version anterior
en `fat32-backups` dentro del run del proyecto, sin llenar A: de respaldos.
Verifica
que los archivos de arranque antiguos no hayan cambiado. No formatea.
