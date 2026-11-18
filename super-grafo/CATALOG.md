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
| [Puerta CASM/Rust](../kernel/syscalls) | diseno | 0 | Recibe operaciones de Ring 3 y comprueba el contrato antes de tocar recursos. |
| [Runtime minimo Rust](../userspace/runtime) | diseno | 3 | Permite ejecutar un programa Rust aislado usando el ABI concedido por CASM. |
| [Servicios Rust](../userspace/services) | diseno | 3 | Aloja servicios con autoridad concedida y politica fuera del kernel. |
| [Aplicaciones Rust](../userspace/apps) | diseno | 3 | Ejercita los servicios y las capacidades con cargas visibles y repetibles. |
| [Construccion y comprobacion host](../tools) | host | host | Valida el catalogo, construye metal64 y registra emision y verificacion reproducibles. |
| [Herencia y procedencia](../heritage) | host | contrato | Conserva los motivos de BMO-X y las huellas de los 38 originales CASM importados. |
| [Ruta y criterios de cierre](../docs) | diseno | contrato | Ordena la construccion de CASM y del kernel por entregas que se puedan comprobar. |
| [Investigacion metal64 0.3](../CASM/traspaso) | investigacion | host | Conserva el intento de runtime/RDTSC con su verificador incompleto y limites escritos. |
| [Primera entrada CASM](../kernel/boot/entry.casm) | host | 0 | Fuente propia minima que ejercita la emision de una entrada de kernel bajo el ABI metal64. |
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
| [Primer arranque UEFI en hardware](../docs/FIRST-BOOT.md) | diseno | host | Ordena la prueba fisica del puente y la entrada CASM minima. |
| [Genesis: prueba aislada en QEMU](../tools/boot/wake.py) | host | host | Prepara imagenes virtuales por run, delega los casos a la sonda QEMU y registra entorno; nunca instala al PC. |
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
| [Contexto de entrega](../kernel/boot/context) | diseno | 0 | Valida el contexto recibido y fija la pila inicial propia. |
| [Memoria fisica](../kernel/mm/physical) | diseno | 0 | Distingue memoria util, reservada y marcos asignados. |
| [Espacios y permisos](../kernel/mm/virtual) | diseno | 0 | Establece espacios virtuales separados y permisos por pagina. |
| [Memoria de usuario](../kernel/mm/user) | diseno | 0 | Valida rangos y copia datos entre anillos. |
| [Cargador SBEF](../kernel/loader) | diseno | 0 | Admite y mapea una imagen SBEF bajo el contrato del proceso. |
| [Buses, recursos y DMA](../kernel/drivers/bus) | qemu | 0 | Descubre xHCI y prueba transporte de comandos con reserva DMA y MMIO supervisora. |
| [Cierre de la base Ring 0](../docs/RING0-PLAN.md) | diseno | contrato | Define la evidencia necesaria para congelar SBEF y el ABI. |
| [Plan de herencia Ring 3](../heritage/RING3-TRANSFER.md) | diseno | contrato | Ordena la transferencia de Ultra_userspace por dependencia real. |
| [Identificacion CPUID](../kernel/arch/x86_64/cpu/identify.casm) | qemu | 0 | Descubre fabricante y hoja basica maxima con CPUID hoja 0. |
| [Guardian del perfil observado](../tools/boot/cpu_config.py) | host | host | Contrasta imagen y resultado antes de publicar profile.config. |
| [Dos perfiles de CPU en QEMU](../kernel/arch/x86_64/cpu/evidence.json) | qemu | host | Vincula dos perfiles observados al mismo paquete verificado. |
| [Pila inicial CASM](../kernel/boot/context/main.casm) | qemu | 0 | Comprueba la entrega y activa una pagina de pila en una reserva del puente. |
| [Gato animado de arranque](../kernel/boot/splash/main.casm) | qemu | 0 | Dibuja y anima el gato en el framebuffer entregado al Ring 0. |
| [Guardian del HEX grafico](../CASM/splash_verify.py) | host | host | Reconstruye mascara y verifica el renderer, IR y presupuesto. |
| [Evidencia de los tres cuadros](../kernel/boot/splash/evidence/qemu.json) | qemu | host | Vincula la animacion observada al paquete exacto y al entorno QEMU. |
| [Rutas de arranque Faggin](../contracts/FAGGIN.md) | diseno | contrato | Define la convergencia de reset y UEFI en una entrega CASM x86-64. |
| [Gato de arranque de mayor resolucion](../kernel/boot/splash/hd/main.casm) | qemu | 0 | Dibuja la silueta de 64 celdas por lado con tres intensidades de ojos. |
| [Primera excepcion #UD](../kernel/arch/x86_64/exceptions/main.casm) | qemu | 0 | Instala una IDT minima y registra el vector y RIP de una excepcion controlada. |
| [Primer marco de RAM](../kernel/mm/physical/main.casm) | qemu | 0 | Prueba escritura y lectura de un marco convencional tras ExitBootServices. |
| [Guardian QEMU del marco](../tools/boot/memory_capture.py) | host | host | Comprueba la primera direccion elegible, la marca fisica y el contexto. |
| [Pesos del build QEMU](../tools/boot/weights.py) | host | host | Mide artefactos en disco y lee la RAM configurada de cada VM. |
| [Propiedad y devolucion de un marco](../kernel/mm/physical/lifecycle/main.casm) | qemu | 0 | Asigna, protege la propiedad, borra y reasigna un marco de 4 KiB. |
| [Tablas propias y alias de datos](../kernel/mm/virtual/main.casm) | qemu | 0 | Instala CR3 propio y separa el mapa supervisor de un alias de usuario. |
| [Fallo de proteccion desde CPL3](../kernel/mm/user/main.casm) | qemu | 0 | Ejecuta un programa fijo en CPL3 y captura el acceso prohibido en Ring 0. |
| [HOST: del ejecutable a SBEF](../tools/host) | host | host | Coordina la inspeccion, admision, diagnostico y publicacion de ejecutables x86-64. |
| [Perfiles y capas del HOST x86-64](../tools/host/profiles.py) | host | host | Registra productores, formatos, reglas PE/ELF y destino exclusivamente x86-64; declara x86-64-v1 como base y niveles SBEF v2 v1-v4 sin prometer traduccion a otras CPU. |
| [Empaquetador ELF64 a SBEF](../tools/host/importers/elf.py) | host | host | Convierte segmentos de un ELF64 estatico a regiones SBEF comprobadas. |
| [Lector SBEF de referencia](../tools/host/sbef/format.py) | host | host | Valida la imagen SBEF y localiza el campo rechazado. |
| [Inspeccion PE32+ x86-64](../tools/host/importers/pe.py) | qemu | host | Inspecciona PE32+ independientemente del productor, aplica relocaciones DIR64 internas y admite perfiles SBEF fijos o freestanding limitados. |
| [Supervisor Rust de Ring 3](../userspace/supervisor) | diseno | 3 | Ordena, configura y recupera servicios desde CPL3. |
| [SBEF ABI 1 y llamadas desde CPL3](../kernel/syscalls/main.casm) | qemu | 0 | Valida SBEF embebido y ejecuta tres entradas SYSCALL. |
| [Banco de toolchains del ABI](../tools/host/toolchains/abi.py) | qemu | host | Construye un cliente comun y coteja los bytes de los stubs ELF. |
| [Revocacion en caliente y diario de fallos](../kernel/mm/virtual/revoke/main.casm) | qemu | 0 | Retira una pagina, invalida la traduccion y reanuda CPL3. |
| [Contrato minimo del cargador SBEF](../contracts/SBEF-LOADER.md) | diseno | contrato | Separa admision, plan de carga, memoria y diagnostico. |
| [Inventario de crates de BMO-X](../heritage/RING3-CRATES.md) | host | host | Agrupa crates del padre por familia y dependencias declaradas. |
| [Reglas de jerarquia de Ring 3](../userspace/POLICY.md) | diseno | contrato | Separa runtime, supervisor, servicios y aplicaciones mediante capacidades. |
| [ULTRA-J: bytecode y tema](../Ultra-J/FORMAT.md) | host | contrato | Fija bytes de instrucciones, estilo por clase y cierre de regiones. |
| [ULTRA-J: verificador y reciclador](../Ultra-J/runtime.py) | host | host | Verifica los dos archivos y ejecuta la recuperacion por region en HOST. |
| [ULTRA-J: compilador inicial](../Ultra-J/compiler.py) | host | host | Traduce el perfil de clases y regiones a instrucciones UJBC verificadas. |
| [ULTRA-J: estructura y estilos](../Ultra-J/view.py) | qemu | host | Mantiene CLI compatible y delega compilacion de estructura y estilos en Ultra-J/ui/. |
| [ULTRA-J: paquete por carpetas](../Ultra-J/package.py) | host | host | Resuelve estilos y crates invocados por la estructura del paquete. |
| [ULTRA-J: presentador x86-64](../Ultra-J/targets/x86_64) | qemu | host | Empaqueta un presentador de Ring 3 para los servicios INVOKE y WAIT de BMO-X2. |
| [Escritorio y espacios de trabajo](../userspace/services/desktop) | qemu | 3 | Compone superficies y gestiona ventanas y cuatro espacios inspirados en Ultra-LinuX. |
| [Teclado y atajos del escritorio](../userspace/services/desktop/src/keyboard.rs) | host | 3 | Convierte eventos de BMO-X en cambios de espacio, foco numerado y movimiento de ventanas. |
| [Teclado y raton USB HID boot](../userspace/services/desktop/src/usb_hid.rs) | host | 3 | Traduce informes USB boot en flancos de teclado, movimiento y botones del raton. |
| [Sonda DOOM C a SBEF](../tools/build-doom-probe.ps1) | qemu | host | Compila la aritmetica original de DoomGeneric y empaqueta un cliente ELF64. |
| [DoomGeneric E1M1 en Ring 3](../tools/build-doom-engine.ps1) | qemu | host | Enlaza DoomGeneric con el runtime C y presenta el juego por CPU. |
| [Mezcla y controles de audio](../userspace/services/audio) | host | 3 | Mezcla PCM estereo de hasta dieciseis fuentes con ganancia acotada. |
| [Prestamo y revocacion DMA](../kernel/drivers/bus/DMA.md) | diseno | contrato | Acota los marcos visibles al dispositivo y controla su devolucion. |
| [Contrato de drivers Ring 3](../contracts/DRIVER-SERVICES.md) | diseno | contrato | Separa protocolos de usuario y concesiones privilegiadas de recursos. |
| [USB HID de Ring 3](../userspace/drivers/usb) | qemu | 3 | Descubre interfaces HID boot, decodifica informes y secuencia configuracion/protocolo/endpoints con terminaciones y plazos comprobados. |
| [Registro ULTRA-J de drivers](../Ultra-J/driver.py) | host | host | Valida registros declarativos de driver y solicita recursos sin concederlos. |
| [REPORTES de entrada](../Reports) | qemu | host | Expone fase USB, motivo, siguiente paso y pulsos de Ring 0 sin necesitar entrada; exporta evidencia en HOST. |
| [ULTRA-J: perfil de estilos](../Ultra-J/ui/style.py) | host | host | Valida el perfil UJC acotado y sus propiedades soportadas. |
| [ULTRA-J: compilador visual](../Ultra-J/ui/view.py) | host | host | Transforma .ujh y reglas en geometria validada y listas UJVI. |
| [RmlUi + ULTRA-J en HOST](../tools/desktop/rmlui) | host | host | Construye RmlUi/FreeType en HOST y empaqueta recursos, UJBC y DLL; prueba el motor C++ con dibujador Rust. |
| [Dibujo CPU Rust para RmlUi](../userspace/services/desktop/src/rmlui.rs) | qemu | 3 | Dibuja triangulos con RGBA o Alpha8 blanco premultiplicado sobre buffers prestados, sin heap ni llamadas de SO. |
| [Sonda SBEF del dibujador comun](../tools/desktop/rmlui/guest.ps1) | qemu | host | Construye el mismo dibujador como SBEF freestanding y compara pixeles reales de QEMU con HOST. |
| [Bienvenida del escritorio en Ring 3](../userspace/services/desktop/src/welcome.rs) | qemu | 3 | Muestra tres fases visuales despues de admision y permisos, entre el gato CASM y el escritorio ULTRA-J. |
| [Recursos de interfaz en memoria](../tools/desktop/rmlui/memory_files.h) | qemu | host | Sustituye acceso a archivos del adaptador por una tabla de recursos inmutables con cursores acotados. |
| [Sesion del motor C++ RmlUi](../tools/desktop/rmlui/engine.cpp) | host | host | Expone reloj, recursos, eventos, destino prestado y omision optativa de cuadros preservados sin cambios, mediante ABI C de aplicacion. |
| [Prueba de sesion y animacion real](../tools/desktop/rmlui/live.py) | host | host | HOST entrega recursos al motor real, avanza tiempo determinista y verifica pixeles, entrada, acciones y rechazos. |
| [Memoria y reposo de la interfaz](../tools/desktop/rmlui/memory.py) | host | host | Mide atlas compactos sin perdida, igualdad visual y trabajo evitado en reposo con reactivacion por entrada. |
| [Motor RmlUi compilado para x86-64](../tools/desktop/rmlui/native/build.py) | host | host | Compila Core real RmlUi, FreeType y libc++/libc++abi como bibliotecas ELF64 sin sustituirlas por una DLL Windows. |
| [Dependencias reales del motor nativo](../tools/desktop/rmlui/native/audit.py) | host | host | Valida archivos ELF de destino, enlaza de verdad las bibliotecas y expone servicios pendientes sin aceptar un relocatable como programa. |
| [Runtime acotado de la interfaz nativa](../tools/desktop/rmlui/native/services.c) | qemu | 3 | Payload Ring 3 compilado y admitido por HOST: une calculo musl sin servicios Linux, heap de 4 MiB y familia new/delete al perfil nativo de un cliente. |
| [Interfaz RmlUi y ULTRA-J nativa](../tools/desktop/rmlui/native/guest.cpp) | qemu | 3 | Payload de escritorio Ring 3 construido por HOST desde C++/Rust/ULTRA-J: carga RML/RCSS/fuentes, dibuja en CPU y ejecuta UJBC con recursos acotados. |
| [Prueba real del motor en CPL3](../tools/boot/rmlui_native_capture.py) | qemu | host | Observa estados, memoria, framebuffer, acciones y cierre del motor real sin simular servicios del invitado. |
| [Politica Rust del escritorio nativo](../userspace/services/desktop/src/native_policy.rs) | qemu | 3 | Adapta DIRECTOR existente a foco, cuatro espacios y nueve posiciones de ventana sin compartir el framebuffer mutable. |
| [Builder UEFI y perfiles xHCI del escritorio](../tools/desktop/rmlui/native/media.py) | qemu | host | Construye el perfil de escritorio FAT32 y las variantes xHCI de teclado/raton para QEMU, sin sustituir el candidato fisico. |
| [Inspeccion acotada de FAT32](../tools/boot/fat32_read.py) | host | host | Lee la primera particion GPT/FAT32 de imagenes de prueba sin modificarlas. |
| [Candidato separado en FAT32 fisico](../tools/desktop/rmlui/native/deploy.ps1) | host | host | Copia exclusivamente el candidato QEMU aprobado al volumen FAT32 A: y verifica hashes. |
| [Entrada UEFI del escritorio nuevo](../tools/desktop/rmlui/native/register-desktop.ps1) | host | host | Registra el candidato validado con un nombre distinto del diagnostico anterior. |
| [Activacion HID con confirmacion](../userspace/drivers/usb/src/activation.rs) | host | 3 | Secuencia configuracion, protocolo por interfaz y endpoints; no supone exito al emitir una peticion. |
| [Contexto interrupt IN USB2](../userspace/drivers/usb/src/xhci.rs) | host | 3 | Calcula DCI e intervalo de cada endpoint descubierto, sin asumir endpoint 0x81. |
| [Eventos xHCI al servicio HID](../userspace/drivers/usb/src/completion.rs) | host | 3 | Coteja eventos copiados antes de avanzar Activation o publicar un informe en InputService. |
| [Retiro del perfil anterior de FAT32](../tools/desktop/rmlui/native/retire-legacy.ps1) | host | host | Archiva con hash y retira exactamente los cuatro archivos del BMO-X2 anterior desregistrado. |
| [Informes USB al escritorio nativo](../tools/desktop/rmlui/native/usb_input.rs) | qemu | 3 | Payload Ring 3 compilado y admitido por HOST: recibe informes escalares mediados y entrega cambios de teclado o raton a RmlUi/DIRECTOR mediante InputService. |
| [xHCI USB2 con dos dispositivos](../kernel/drivers/bus/native/controller.inc) | qemu | 0 | Sonda ASM transitoria de Ring 0: descubre bancos MMIO, configura dos slots y entrega informes HID mediados al escritorio; no reemplaza la implementacion estable CASM. |
| [Presentacion GOP del cursor y barra por regiones](../kernel/drivers/bus/native/gop_cursor.inc) | qemu | 0 | Sonda ASM transitoria de Ring 0: copia al GOP una caja de cursor o la franja superior fija por INVOKE 10 en escala 1. |

## Dependencias declaradas

| Quien usa | De quien depende | Clase |
|---|---|---|
| ultra-j-package | ultra-j-compiler | codigo |
| ultra-j-package | ultra-j-view | codigo |
| ultra-j-x86-view | ultra-j-view | codigo |
| ultra-j-view | ultra-j-format | plan |
| ultra-j-compiler | ultra-j-recycler | codigo |
| ultra-j-recycler | ultra-j-format | verificacion |
| ultra-j-recycler | desktop-workspaces | plan |
| host-pipeline | sbef-host-pack | codigo |
| host-pipeline | host-profile-registry | codigo |
| host-profile-registry | sbef-host-pack | codigo |
| host-profile-registry | sbef-host-reader | codigo |
| host-profile-registry | sbef-host-pe | codigo |
| host-pipeline | sbef-host-reader | codigo |
| host-pipeline | sbef-host-pe | codigo |
| abi-toolchains | host-pipeline | verificacion |
| desktop-usb-hid | desktop-keyboard | codigo |
| physical-boot | boot-bridge | plan |
| physical-boot | qemu-runner | plan |
| physical-boot | boot-context | plan |
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
| drivers | mm | plan |
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
| stop-source | stop-contract | verificacion |
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
| boot-context | boot | plan |
| boot-context | stop-source | plan |
| physical-memory | mm | plan |
| physical-memory | boot-context | plan |
| virtual-memory | physical-memory | plan |
| user-memory | virtual-memory | plan |
| user-memory | x86_64-exceptions | plan |
| sbef-loader | sbef | plan |
| device-bus | drivers | plan |
| device-bus | virtual-memory | plan |
| ring0-base-gate | entry-budget | plan |
| ring0-base-gate | sbef-loader | plan |
| ring3-transfer | ring0-base-gate | plan |
| x86_64-cpu | boot-context | plan |
| rust-runtime | ring3-transfer | plan |
| cpu-identification | x86_64-cpu | codigo |
| cpu-identification | stop-verifier | verificacion |
| cpu-profile-guardian | cpu-identification | verificacion |
| cpu-profile-guardian | qemu-runner | verificacion |
| cpu-profile-qemu | cpu-profile-guardian | verificacion |
| boot-stack | boot-context | codigo |
| boot-stack | stop-verifier | verificacion |
| x86_64-exceptions | boot-stack | plan |
| boot-splash | boot-bridge | plan |
| boot-splash | splash-guardian | verificacion |
| splash-guardian | entry-budget | verificacion |
| splash-qemu | boot-splash | verificacion |
| faggin-contract | contracts | plan |
| boot-splash-hd | boot-splash | verificacion |
| boot-splash-hd | splash-guardian | verificacion |
| fault-ud | x86_64-exceptions | plan |
| fault-ud | stop-verifier | verificacion |
| physical-memory | ram-frame | plan |
| ram-frame | boot-context | codigo |
| ram-frame | stop-verifier | verificacion |
| ram-qemu | ram-frame | verificacion |
| qemu-weights | ram-qemu | verificacion |
| physical-memory | ram-frame-cycle | plan |
| ram-frame-cycle | ram-frame | codigo |
| ram-frame-cycle | ram-qemu | verificacion |
| virtual-memory | own-page-tables | plan |
| own-page-tables | ram-frame | codigo |
| own-page-tables | stop-verifier | verificacion |
| user-protection-fault | own-page-tables | plan |
| user-protection-fault | fault-ud | plan |
| sbef-host-pack | sbef | codigo |
| sbef-loader | sbef-host-pack | verificacion |
| sbef-host-pack | sbef-host-reader | verificacion |
| sbef-loader | sbef-host-reader | verificacion |
| userspace-supervisor | rust-services | plan |
| userspace-supervisor | rust-runtime | plan |
| sbef-loader | abi-probe | verificacion |
| abi-probe | user-protection-fault | plan |
| abi-toolchains | sbef-host-pack | generacion |
| hot-unmap | user-protection-fault | plan |
| virtual-memory | hot-unmap | verificacion |
| sbef-loader | sbef-loader-boundary | plan |
| userspace-supervisor | ring3-crate-inventory | plan |
| userspace-supervisor | ring3-policy | plan |
| desktop-workspaces | userspace-supervisor | plan |
| device-bus | dma-lease | plan |
| dma-lease | hot-unmap | plan |
| desktop-keyboard | desktop-workspaces | codigo |
| doom-fixed-probe | sbef-loader-boundary | plan |
| doom-fixed-probe | sbef-host-pack | generacion |
| doom-engine | doom-fixed-probe | verificacion |
| doom-engine | sbef-host-pack | generacion |
| audio-mixer | dma-lease | plan |
| desktop-workspaces | audio-mixer | plan |
| usb-ring3-driver | driver-services-contract | codigo |
| driver-services-contract | dma-lease | plan |
| desktop-workspaces | usb-ring3-driver | codigo |
| ultra-j-driver-registration | driver-services-contract | codigo |
| ultra-j-driver-registration | sbef-host-reader | verificacion |
| diagnostic-reports | device-bus | codigo |
| diagnostic-reports | desktop-workspaces | codigo |
| ultra-j-view | ultra-j-view-compiler | codigo |
| ultra-j-view-compiler | ultra-j-style-profile | codigo |
| ultra-j-view-compiler | ultra-j-format | generacion |
| rmlui-host-preview | ultra-j-compiler | codigo |
| rmlui-host-preview | ultra-j-recycler | codigo |
| rmlui-host-preview | rmlui-rust-raster | codigo |
| rmlui-raster-probe | rmlui-rust-raster | codigo |
| rmlui-raster-probe | abi-probe | verificacion |
| desktop-welcome | abi-bef2 | codigo |
| desktop-workspaces | desktop-welcome | codigo |
| rmlui-host-preview | rmlui-engine-session | codigo |
| rmlui-engine-session | rmlui-memory-resources | codigo |
| rmlui-engine-session | rmlui-rust-raster | codigo |
| rmlui-live-validation | rmlui-engine-session | verificacion |
| rmlui-live-validation | ultra-j-compiler | codigo |
| rmlui-live-validation | ultra-j-recycler | codigo |
| rmlui-memory-budget | rmlui-engine-session | verificacion |
| rmlui-memory-budget | rmlui-raster-probe | verificacion |
| rmlui-native-build | rmlui-native-audit | codigo |
| rmlui-engine-session | rmlui-native-build | codigo |
| rmlui-native-application | rmlui-native-build | codigo |
| rmlui-native-application | rmlui-native-runtime | codigo |
| rmlui-native-application | rmlui-rust-raster | codigo |
| rmlui-native-application | ultra-j-compiler | codigo |
| rmlui-native-validation | rmlui-native-application | codigo |
| rmlui-native-validation | rmlui-native-audit | codigo |
| rmlui-native-application | rmlui-desktop-policy | codigo |
| rmlui-fat32-media | rmlui-native-application | codigo |
| rmlui-fat32-media | rmlui-fat32-reader | codigo |
| rmlui-metal-candidate | rmlui-fat32-media | codigo |
| rmlui-desktop-firmware-entry | rmlui-metal-candidate | codigo |
| usb-ring3-driver | usb-ring3-activation | codigo |
| usb-ring3-activation | usb-ring3-endpoint-plan | codigo |
| usb-ring3-driver | usb-ring3-completion | codigo |
| usb-ring3-completion | usb-ring3-activation | codigo |
| rmlui-retire-legacy-files | rmlui-metal-candidate | codigo |
| rmlui-native-application | rmlui-native-usb-input | codigo |
| rmlui-native-usb-input | usb-ring3-driver | codigo |
| rmlui-fat32-media | device-bus | codigo |
| rmlui-fat32-media | rmlui-native-usb-input | codigo |
| rmlui-native-usb-input | rmlui-usb-dual | codigo |
| rmlui-gop-cursor-region | rmlui-usb-dual | codigo |

El grafo de codigo de SG se calcula desde sus fuentes. Estas relaciones tambien incluyen el plan y no se presentan como llamadas ejecutadas.
