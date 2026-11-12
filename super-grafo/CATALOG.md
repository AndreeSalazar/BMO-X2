# Catalogo de nodos de BMO-X2

> Generado desde nodes.json. Relaciones de plan separadas del codigo.

| Nodo | Estado | Anillo | Responsabilidad |
|---|---|---|---|
| [Contratos de BMO-X2](../contracts) | diseno | contrato | Fija destino, imagen, memoria, permisos y frontera CASM/Rust. |
| [Programas CASM](../CASM/examples) | heredado | host | Programas pequenos para comprobar fuente, semantica y bytes exactos. |
| [Entrada del compilador](../CASM/src/main.c) | heredado | host | Lee una fuente acotada, invoca analisis y emision y comunica el rechazo. |
| [Entrada y diagnosticos del frontend](../CASM/src/frontend.c) | host | host | Valida el limite de fuente y despacha los rechazos reales de los modulos del frontend. |
| [IR y tipos metal64](../CASM/src/casm.h) | host | host | Contrato privado de IR con dos depositos compartidos acotados, sin buffers maximos por elemento. |
| [Codificador x86-64](../CASM/src/emitter.c) | heredado | host | Escribe las instrucciones y datos propios de metal64; no usa un backend externo. |
| [Contrato HEX preciso](../CASM/contracts) | diseno | contrato | Define el significado de HEX preciso: bytes exactos y evidencia de su correspondencia. |
| [Verificador metal64](../CASM/verify.py) | heredado | host | Reconstruye bytes y enteros por separado y solo admite el paquete si coinciden. |
| [Banco metal64](../CASM/test.py) | host | host | Comprueba casos validos, rechazos de fuente, mutaciones y el saludo de oro. |
| [Compilador escrito en CASM](../CASM/native/compiler.body.casm) | heredado | host | Analizador y emisor Native expresados en el propio lenguaje. |
| [Runtime del anfitrion Native](../CASM/native/runtime.py) | heredado | host | Construye las plantillas de servicios y trampas usadas por Native en Linux. |
| [Fuente Native completa](../CASM/native/compiler.casm) | heredado | host | Fuente completa del compilador: cuerpo CASM mas constantes del runtime. |
| [Verificador Native](../CASM/native/verify.py) | heredado | host | Reconoce el subconjunto de instrucciones, destinos, marcos y buffers de Native. |
| [Salida sin servicios Linux](../CASM/native/freestanding.py) | heredado | host | Deriva un modulo de calculo x86-64 sin runtime Linux, con permisos y trampas. |
| [CASM para el metal privilegiado](../CASM/x86_64) | diseno | host | Define la ampliacion del lenguaje que permite expresar el kernel sin perder control de bytes y efectos. |
| [Arranque del kernel](../kernel/boot) | diseno | 0 | Recibe una maquina y una imagen bajo un contrato de entrega verificable. |
| [CPU x86-64](../kernel/arch/x86_64/cpu) | diseno | 0 | Descubre capacidades CPU y prepara descriptores y estado privilegiado con limites explicitos. |
| [Excepciones x86-64](../kernel/arch/x86_64/exceptions) | diseno | 0 | Contiene fallos de CPU y preserva el estado necesario para explicar quien fallo y donde. |
| [Memoria y aislamiento](../kernel/mm) | diseno | 0 | Asigna paginas y separa memoria del kernel, procesos y aparatos. |
| [Capacidades](../kernel/capabilities) | diseno | 0 | Concede autoridad explicita y comprueba propietario, derechos y vigencia. |
| [Puerta CASM/Rust](../kernel/syscalls) | diseno | 0 | Recibe operaciones de Ring 3 y comprueba el contrato antes de tocar recursos. |
| [Runtime minimo Rust](../userspace/runtime) | diseno | 3 | Permite ejecutar un programa Rust aislado usando el ABI concedido por CASM. |
| [Servicios Rust](../userspace/services) | diseno | 3 | Aloja servicios con autoridad concedida y politica fuera del kernel. |
| [Aplicaciones Rust](../userspace/apps) | diseno | 3 | Ejercita los servicios y las capacidades con cargas visibles y repetibles. |
| [Construccion y comprobacion host](../tools) | host | host | Valida el catalogo, construye metal64 y registra emision y verificacion reproducibles. |
| [Herencia y procedencia](../heritage) | host | contrato | Conserva los motivos de BMO-X y las huellas de los 38 originales CASM importados. |
| [Ruta y criterios de cierre](../docs) | diseno | contrato | Ordena la construccion de CASM y del kernel por entregas que se puedan comprobar. |
| [Investigacion metal64 0.3](../CASM/traspaso) | investigacion | host | Conserva el intento de runtime/RDTSC con su verificador incompleto y limites escritos. |
| [Primera entrada CASM](../kernel/boot/entry.casm) | host | 0 | Fuente propia minima que ejercita la emision de una entrada de kernel bajo el ABI metal64. |
| [Interrupciones de hardware](../kernel/arch/x86_64/interrupts) | diseno | 0 | Encamina IRQ con un contrato de entrada y reconocimiento separado de las excepciones. |
| [Inicializacion del kernel](../kernel/init) | diseno | 0 | Ordena fases y precondiciones del kernel sin esconder los fallos de un subsistema. |
| [Reloj y plazos](../kernel/time) | diseno | 0 | Ofrece tiempo monotono y plazos medibles antes de introducir planificacion. |
| [Planificacion](../kernel/sched) | diseno | 0 | Gestiona ejecucion y espera con contexto y presupuesto definidos. |
| [Comunicacion entre procesos](../kernel/ipc) | diseno | 0 | Transporta mensajes y prestamos con autoridad y limites comprobados. |
| [Frontera de dispositivos](../kernel/drivers) | diseno | 0 | Aisla mecanismos de dispositivos del resto del kernel y explicita acceso a puertos/MMIO/DMA. |
| [Lexico](../CASM/src/frontend/lexer.c) | host | host | Reconoce tokens ASCII y posiciones sin interpretar los valores. |
| [Nombres y tipos](../CASM/src/frontend/symbols.c) | host | host | Comprueba nombres reservados, declarados y tipos disponibles. |
| [Enteros exactos](../CASM/src/frontend/integers.c) | host | host | Evalua expresiones de constantes con anchura declarada y RPN comprobable. |
| [Sintaxis metal64](../CASM/src/frontend/parser.c) | host | host | Forma declaraciones, llamadas y la entrada del perfil metal64. |
| [Almacenamiento compartido](../CASM/src/model/storage.c) | host | host | Guarda datos y RPN en depositos comprobados dentro del modelo del anfitrion. |
| [Tipos de CPU metal64](../CASM/src/model/types.c) | host | host | Tabla generada de nombres, anchuras y signo de los ocho tipos metal64. |
| [Interfaces del frontend](../CASM/src/frontend/internal.h) | host | host | Declara estado privado del parser, codigos de diagnostico e interfaces entre modulos. |
| [Manifest de construccion](../CASM/sources.json) | host | host | Enumera las mismas fuentes y cabeceras x86-64 para Windows y Linux. |
| [Invariantes de memoria](../CASM/tests/workspace.c) | host | host | Prueba extremos, estabilidad y rechazo sin escritura parcial del almacenamiento. |
| [Comparacion y medida](../CASM/tests/maturity.py) | host | host | Reconstruye d2575a8 y exige la misma emision y diagnosticos del compilador reorganizado. |
| [Listas y jerarquia de CASM](../CASM/catalog.json) | host | host | Define tipos, sintaxis, IR, codificaciones y capacidades por estado dentro de una jerarquia versionada. |
| [Generacion desde las listas](../CASM/catalog.py) | host | host | Valida la jerarquia x86-64 y genera la tabla de tipos real del compilador. |
| [Pruebas de las listas](../CASM/tests/test_catalog.py) | host | host | Exige que las listas no amplien silenciosamente lo que el compilador puede aceptar. |
| [Espacio de trabajo BMO-X2](../BMO-X2.sg-workspace) | host | host | Define la raiz portable y los valores iniciales de vista y panel de SUPER GRAFO. |
| [Contrato CASM Ring 0](../CASM/contracts/RING0.md) | host | host | Fija el destino exclusivo del kernel y explica el vector de entrada sin atribuir privilegio al formato HEX. |
| [Lectura comprobada del HEX](../tools/hex_report.py) | host | host | Repite el verificador y contrasta el paquete antes de mostrar linea, offsets, clase y bytes. |
| [Genesis G0 y G1](../kernel/boot/genesis) | qemu | host | Contrato y fuente minima observable con salida mediante el cargador. |
| [Genesis: fuente CASM](../kernel/boot/genesis/main.casm) | qemu | 0 | Declara GENESIS, CR/LF y retorno; requiere la tabla de servicios metal64. |
| [Genesis: vector manual](../kernel/boot/genesis/expected.hex) | host | host | Fija 22 bytes independientes del emisor: 12 de instrucciones y 10 de datos. |
| [Genesis: guardian de bytes y tamano](../tools/genesis.py) | host | host | Exige fuente congelada exacta, verificacion independiente, vector manual y paquete menor de 512 bytes. |
| [Genesis: colores y flujo vertical](../super-grafo/genesis.json) | host | host | Define posiciones y colores por responsabilidad, con un motivo visible por archivo. |
| [Puente UEFI provisional](../kernel/boot/bridge) | heredado | host | Bootstrap HEX manual importado de TALK-CPU; recibe firmware y entrega contexto metal64 al payload CASM. |
| [Genesis: prueba aislada en QEMU](../tools/boot/wake.py) | host | host | Prepara imagenes virtuales por run y registra entorno; nunca instala al PC. |
| [Genesis: evidencia de ejecucion](../kernel/boot/genesis/evidence/qemu.json) | qemu | host | Siete casos observados en QEMU: cuerpo cargado exacto, texto, CPL=0, retorno y rechazos. |
| [Rutas host compatibles 5.1 y 7](../tools/paths.ps1) | host | host | Forma nombres relativos para registrar huellas; rechaza rutas externas sin usar GetRelativePath de .NET Core. |
| [Regresion de rutas y versiones host](../tools/tests/paths.ps1) | host | host | Comprueba nombres con espacios, normalizacion y rechazos de rutas externas en Windows PowerShell 5.1 y PowerShell 7. |
| [Contrato parada Ring 0](../CASM/profiles/ring0-stop.json) | host | host | Define gramatica cerrada, entrada, efectos y bytes de ring0-stop-0.1. |
| [Fuente de parada propia](../kernel/boot/stop/main.casm) | qemu | 0 | Ordena detener la CPU desde codigo propio. |
| [Frontend y emisor de parada](../CASM/src/kernel/stop.c) | host | host | Analiza el terminal cerrado y emite IR3 y bytes propios. |
| [Vector manual de parada](../kernel/boot/stop/expected.hex) | host | host | Fija la referencia independiente FA F4 EB FD. |
| [Verificador independiente de parada](../CASM/stop_verify.py) | host | host | Reconoce fuente, IR3 y bytes sin invocar el compilador. |
| [Pruebas del perfil privilegiado](../CASM/tests/test_stop.py) | host | host | Prueba fronteras de gramatica, perfil, IR y emision. |
| [Evidencia QEMU parada S1](../kernel/boot/stop/evidence/qemu.json) | qemu | host | Registra parada propia tras ExitBootServices y seis casos negativos. |
| [BEF2 y ABI de BMO-X](../contracts/ABI-BEF2.md) | diseno | contrato | Conserva el formato y las dos puertas del padre como referencia para SBEF. |
| [Presupuesto de la entrada Ring 0](../CASM/entry_budget.py) | host | host | Acota el paquete binario de la entrada a menos de 512 bytes. |
| [SBEF y congelacion del ABI](../contracts/SBEF.md) | diseno | contrato | Define la evolucion de BEF2 para admitir programas x86-64 en BMO-X2. |

## Dependencias declaradas

| Quien usa | De quien depende | Clase |
|---|---|---|
| compiler-entry | frontend | codigo |
| compiler-entry | encoder-x86_64 | codigo |
| compiler-entry | metal64-ir | codigo |
| frontend | metal64-ir | codigo |
| encoder-x86_64 | metal64-ir | codigo |
| metal64-verifier | hex-contract | verificacion |
| metal64-tests | compiler-entry | verificacion |
| metal64-tests | metal64-verifier | verificacion |
| metal64-tests | source | verificacion |
| native-source | native-body | generacion |
| native-source | native-runtime | generacion |
| native-verifier | native-runtime | codigo |
| freestanding | native-verifier | codigo |
| freestanding | native-runtime | codigo |
| kernel-profile | contracts | plan |
| kernel-profile | native-body | plan |
| kernel-profile | hex-contract | plan |
| boot | kernel-profile | plan |
| boot | contracts | plan |
| x86_64-cpu | boot | plan |
| x86_64-exceptions | x86_64-cpu | plan |
| mm | x86_64-cpu | plan |
| capabilities | mm | plan |
| capabilities | contracts | plan |
| syscalls | capabilities | plan |
| syscalls | x86_64-exceptions | plan |
| rust-runtime | syscalls | plan |
| rust-services | rust-runtime | plan |
| rust-apps | rust-services | plan |
| tools | compiler-entry | codigo |
| tools | metal64-verifier | codigo |
| tools | metal64-tests | verificacion |
| roadmap | contracts | plan |
| roadmap | heritage | plan |
| research-metal64-03 | frontend | plan |
| research-metal64-03 | encoder-x86_64 | plan |
| research-metal64-03 | metal64-verifier | plan |
| boot | kernel-entry | plan |
| kernel-entry | metal64-verifier | verificacion |
| x86_64-interrupts | x86_64-cpu | plan |
| x86_64-interrupts | x86_64-exceptions | plan |
| init | x86_64-exceptions | plan |
| init | mm | plan |
| time | x86_64-interrupts | plan |
| sched | time | plan |
| sched | init | plan |
| ipc | capabilities | plan |
| drivers | mm | plan |
| drivers | x86_64-interrupts | plan |
| frontend | grammar | codigo |
| frontend | frontend-contract | codigo |
| frontend-contract | metal64-ir | codigo |
| lexer | frontend-contract | codigo |
| symbols | frontend-contract | codigo |
| symbols | model-types | codigo |
| integers | frontend-contract | codigo |
| integers | symbols | codigo |
| integers | model-storage | codigo |
| grammar | lexer | codigo |
| grammar | symbols | codigo |
| grammar | integers | codigo |
| grammar | model-storage | codigo |
| model-types | metal64-ir | codigo |
| model-storage | metal64-ir | codigo |
| workspace-tests | model-storage | verificacion |
| maturity-meter | workspace-tests | verificacion |
| maturity-meter | compiler-entry | verificacion |
| maturity-meter | metal64-verifier | verificacion |
| tools | compiler-sources | generacion |
| compiler-sources | frontend | generacion |
| compiler-sources | lexer | generacion |
| compiler-sources | symbols | generacion |
| compiler-sources | integers | generacion |
| compiler-sources | grammar | generacion |
| compiler-sources | model-storage | generacion |
| compiler-sources | model-types | generacion |
| compiler-sources | frontend-contract | generacion |
| model-types | casm-catalog | generacion |
| model-types | catalog-generator | generacion |
| catalog-generator | casm-catalog | codigo |
| catalog-generator | metal64-verifier | verificacion |
| catalog-tests | catalog-generator | verificacion |
| catalog-tests | casm-catalog | verificacion |
| tools | catalog-generator | generacion |
| compiler-sources | casm-catalog | generacion |
| compiler-sources | catalog-generator | generacion |
| workspace | casm-catalog | plan |
| tools | workspace | codigo |
| hex-reader | metal64-verifier | verificacion |
| hex-reader | ring0-contract | plan |
| ring0-contract | kernel-profile | plan |
| genesis-source | genesis | plan |
| genesis-source | frontend | plan |
| genesis-guardian | genesis-vector | verificacion |
| genesis-guardian | genesis-source | verificacion |
| genesis-guardian | metal64-verifier | verificacion |
| genesis-graph | genesis | plan |
| qemu-runner | boot-bridge | generacion |
| qemu-runner | genesis-guardian | verificacion |
| genesis-qemu | qemu-runner | verificacion |
| genesis-qemu | genesis-source | verificacion |
| genesis-qemu | genesis | verificacion |
| genesis-source | boot-bridge | plan |
| tools | host-paths | codigo |
| host-path-tests | host-paths | verificacion |
| stop-source | stop-contract | codigo |
| stop-compiler | stop-contract | codigo |
| stop-compiler | lexer | codigo |
| compiler-entry | stop-compiler | codigo |
| stop-verifier | stop-contract | verificacion |
| stop-verifier | stop-vector | verificacion |
| stop-tests | stop-compiler | verificacion |
| stop-tests | stop-verifier | verificacion |
| stop-qemu | stop-source | verificacion |
| stop-qemu | stop-verifier | verificacion |
| stop-qemu | qemu-runner | verificacion |
| stop-qemu | boot-bridge | verificacion |
| abi-bef2 | contracts | plan |
| syscalls | abi-bef2 | plan |
| rust-runtime | abi-bef2 | plan |
| stop-verifier | entry-budget | verificacion |
| genesis-guardian | entry-budget | verificacion |
| sbef | abi-bef2 | plan |
| sbef | mm | plan |
| rust-runtime | sbef | plan |

El grafo de codigo de SG se calcula desde sus fuentes. Estas relaciones tambien incluyen el plan y no se presentan como llamadas ejecutadas.
