# Notas de BMO-X2

> Generadas desde nodes.json; HEREDADO y DISENO no significan ejecutado aqui.

## contracts

Fija destino, imagen, memoria, permisos y frontera CASM/Rust.

Estado: DISENO. Anillo: contrato. Lenguaje: contrato.
Entrada: Decisiones del propietario y lecciones verificables de BMO-X.
Salida: Contratos versionados y pruebas de sus invariantes.
Depende de: contrato propio sin dependencias en este catalogo.
Aceptacion: Cada campo del ABI y formato tiene productor, consumidor y caso negativo.
Pendiente: Definir el primer ABI BMO-X2 y su imagen de carga.

## CASM/examples

Programas pequenos para comprobar fuente, semantica y bytes exactos.

Estado: HEREDADO. Anillo: host. Lenguaje: CASM.
Entrada: Fuente ASCII del perfil metal64 0.2.
Salida: Fuente congelada por cada compilacion.
Depende de: contrato propio sin dependencias en este catalogo.
Aceptacion: Hello conserva su paquete de oro; enteros conserva resultados y rechazos.
Pendiente: Ejemplos de kernel conforme se habiliten operaciones de ejecucion.

## CASM/src/main.c

Lee una fuente acotada, invoca analisis y emision y comunica el rechazo.

Estado: HEREDADO. Anillo: host. Lenguaje: C semilla.
Entrada: Ruta fuente y rutas nuevas de HEX/IR.
Salida: CasmProgram analizado y salida de emision sin publicar paquete.
Depende de: Lexico, sintaxis y semantica (codigo), Codificador x86-64 (codigo), IR y tipos metal64 (codigo).
Aceptacion: Casos HOST-READ, SOURCE-SIZE, HOST-WRITE y HOST-MEMORY donde el SO permite probarlo.
Pendiente: Portar el anfitrion del compilador propio cuando BMO-X2 tenga servicios de archivos.

## CASM/src/frontend.c

Reconoce el lenguaje metal64 y calcula enteros exactos con reglas explicitas.

Estado: HEREDADO. Anillo: host. Lenguaje: C semilla.
Entrada: Bytes de fuente ASCII acotada.
Salida: Programa, tipos, constantes, llamadas y origen fuente.
Depende de: IR y tipos metal64 (codigo).
Aceptacion: Cada regla rechaza su caso; reparto futuro conserva HEX/IR y diagnosticos del banco.
Pendiente: Separar lexer, parser, nombres y enteros; incorporar semantica de runtime para el kernel.

## CASM/src/casm.h

Contrato acotado de datos entre analisis y emisor metal64.

Estado: HEREDADO. Anillo: host. Lenguaje: C semilla.
Entrada: Declaraciones, expresiones y limites del perfil.
Salida: CasmProgram, CasmInteger, CasmConstant y CasmCall.
Depende de: contrato propio sin dependencias en este catalogo.
Aceptacion: Emisor y verificador coinciden en tipos, medidas y valores; limites ejercitados.
Pendiente: IR versionada del kernel con flujo, funciones, efectos y trampas.

## CASM/src/emitter.c

Escribe las instrucciones y datos propios de metal64; no usa un backend externo.

Estado: HEREDADO. Anillo: host. Lenguaje: C semilla.
Entrada: CasmProgram valido.
Salida: program.hex y program.ir.json sin paquete admitido.
Depende de: IR y tipos metal64 (codigo).
Aceptacion: Bytes de oro, desplazamientos RIP y regiones coinciden con el verificador independiente.
Pendiente: Codificaciones y ABI del subconjunto de CPU que requiera el kernel.

## CASM/contracts

Define el significado de HEX preciso: bytes exactos y evidencia de su correspondencia.

Estado: DISENO. Anillo: contrato. Lenguaje: contrato.
Entrada: Fuente congelada, perfil, IR, bytes y origen de herramientas.
Salida: Contrato fuente -> IR -> HEX -> bytes, con entrada, regiones, medidas y huellas.
Depende de: contrato propio sin dependencias en este catalogo.
Aceptacion: Roundtrip HEX/bytes exacto y rechazo de IR, opcode, desplazamiento o dato alterado.
Pendiente: Extender el contrato actual a trampas y relocaciones del kernel; HEX no acredita por si solo ejecucion.

## CASM/verify.py

Reconstruye bytes y enteros por separado y solo admite el paquete si coinciden.

Estado: HEREDADO. Anillo: host. Lenguaje: Python control.
Entrada: Fuente congelada, HEX e IR.
Salida: Paquete FAGRAW64 e informe con huellas, o rechazo.
Depende de: Contrato HEX preciso (verificacion).
Aceptacion: Mutaciones de una sola propiedad rechazan por la regla esperada y no publican paquete.
Pendiente: Comprobar instrucciones y efectos nuevos antes de permitir su publicacion.

## CASM/test.py

Comprueba casos validos, rechazos de fuente, mutaciones y el saludo de oro.

Estado: HOST. Anillo: host. Lenguaje: Python control.
Entrada: Semilla del anfitrion y programas/casos del banco.
Salida: test-results.json con aprobados y omisiones explicitas.
Depende de: Entrada del compilador (verificacion), Verificador metal64 (verificacion), Programas CASM (verificacion).
Aceptacion: Todos los casos aplicables pasan; RLIMIT_DATA se omite explicitamente en Windows.
Pendiente: Repetir banco completo Linux y ejecucion QEMU en esta copia.

## CASM/native/compiler.body.casm

Analizador y emisor Native expresados en el propio lenguaje.

Estado: HEREDADO. Anillo: host. Lenguaje: CASM.
Entrada: Fuente Native: u64, funciones, control y buffers.
Salida: Funciones del compilador que producen ELF/HEX x86-64.
Depende de: contrato propio sin dependencias en este catalogo.
Aceptacion: Generaciones identicas desde dos semillas y otra fuente compilada en el taller Linux.
Pendiente: Repetir evidencia aqui y definir la ampliacion freestanding privilegiada.

## CASM/native/runtime.py

Construye las plantillas de servicios y trampas usadas por Native en Linux.

Estado: HEREDADO. Anillo: host. Lenguaje: Python generador.
Entrada: Contrato de servicios Linux y layout de datos Native.
Salida: Bytes y etiquetas que se incorporan a la fuente completa.
Depende de: contrato propio sin dependencias en este catalogo.
Aceptacion: Plantillas auditadas; trampas y direcciones coinciden con el verificador Native.
Pendiente: Backend de servicios BMO-X2 separado; ningun syscall Linux implicito en Ring 0.

## CASM/native/compiler.casm

Fuente completa del compilador: cuerpo CASM mas constantes del runtime.

Estado: HEREDADO. Anillo: host. Lenguaje: CASM.
Entrada: compiler.body.casm y runtime.py, ensamblados por seed.py.
Salida: Fuente reproducible para las generaciones Native.
Depende de: Compilador escrito en CASM (generacion), Runtime del anfitrion Native (generacion).
Aceptacion: seed.py exige que la fuente completa coincida con cuerpo y runtime; no se genera desde el ejecutable.
Pendiente: Repetir autocompilacion Linux antes de cambiar la generacion heredada.

## CASM/native/verify.py

Reconoce el subconjunto de instrucciones, destinos, marcos y buffers de Native.

Estado: HEREDADO. Anillo: host. Lenguaje: Python control.
Entrada: ELF x86-64 Native y contrato de runtime.
Salida: Admision acotada o rechazo; no valida todo ejecutable x86.
Depende de: Runtime del anfitrion Native (codigo).
Aceptacion: Mutaciones de instrucciones, flujo, pila y direcciones rechazan; fuentes nuevas siguen admitidas.
Pendiente: Contrato de verificacion para las futuras operaciones privilegiadas.

## CASM/native/freestanding.py

Deriva un modulo de calculo x86-64 sin runtime Linux, con permisos y trampas.

Estado: HEREDADO. Anillo: host. Lenguaje: Python adaptador.
Entrada: ELF Native comprobado, sin llamadas a servicios prohibidos.
Salida: module.json con segmentos, entrada, trampas y procedencia.
Depende de: Verificador Native (codigo), Runtime del anfitrion Native (codigo).
Aceptacion: Calculos, SIGILL y mutaciones pasan en procesos aislados Linux/QEMU; cargador aplica RX/RW/NX.
Pendiente: Cargador propio: este modulo no es una imagen EFI ni un kernel.

## CASM/x86_64

Define la ampliacion del lenguaje que permite expresar el kernel sin perder control de bytes y efectos.

Estado: DISENO. Anillo: host. Lenguaje: CASM especificacion.
Entrada: Programas minimos de CPU, memoria y excepciones que exige BMO-X2.
Salida: Semantica, IR, emision propia y verificacion de operaciones privilegiadas.
Depende de: Contratos de BMO-X2 (plan), Compilador escrito en CASM (plan), Contrato HEX preciso (plan).
Aceptacion: Cada operacion tiene codificacion independiente, efecto autorizado y prueba QEMU positiva/negativa.
Pendiente: MMIO/volatile, CR/MSR, puertos, atomicos, descriptores, entradas de excepcion y cambios de anillo.

## kernel/boot

Recibe una maquina y una imagen bajo un contrato de entrega verificable.

Estado: DISENO. Anillo: 0. Lenguaje: CASM.
Entrada: Estado x86-64, memoria y framebuffer entregados por una cadena de arranque especificada.
Salida: Entrada del kernel CASM, diagnostico y estado de fallo controlado.
Depende de: CASM para el metal privilegiado (plan), Contratos de BMO-X2 (plan), Primera entrada CASM (plan).
Aceptacion: QEMU muestra entrada real y rechaza contexto/imagen incompatibles; se conserva recuperacion.
Pendiente: Elegir la cadena de carga y contexto; entry.casm es solo una sonda compilada y verificada en host.

## kernel/arch/x86_64/cpu

Descubre capacidades CPU y prepara descriptores y estado privilegiado con limites explicitos.

Estado: DISENO. Anillo: 0. Lenguaje: CASM.
Entrada: Contrato de arranque y operaciones privilegiadas CASM.
Salida: Estado CPU apto para excepciones y aislamiento de Ring 3.
Depende de: Arranque del kernel (plan).
Aceptacion: CPUID y limites observados en QEMU; no se confunde el perfil del Ryzen con todo x86-64.
Pendiente: GDT/TSS, modos, registros de control y requisitos minimos del perfil inicial.

## kernel/arch/x86_64/exceptions

Contiene fallos de CPU y preserva el estado necesario para explicar quien fallo y donde.

Estado: DISENO. Anillo: 0. Lenguaje: CASM.
Entrada: CPU preparada y marcos de excepcion definidos.
Salida: Diagnostico, terminacion del proceso o parada controlada segun origen.
Depende de: CPU x86-64 (plan).
Aceptacion: #UD/#PF de Ring 3 terminan ese proceso; el kernel conserva control y evidencia.
Pendiente: IDT, entradas, pilas de excepcion, retorno e interrupciones de hardware.

## kernel/mm

Asigna paginas y separa memoria del kernel, procesos y aparatos.

Estado: DISENO. Anillo: 0. Lenguaje: CASM.
Entrada: Mapa de memoria, capacidades CPU e intervalos reservados.
Salida: Paginas con propietario, tablas, permisos y devolucion definidos.
Depende de: CPU x86-64 (plan).
Aceptacion: Ring 3 no escribe kernel ni ejecuta datos NX; rangos invalidos y desbordes se rechazan.
Pendiente: Asignador, paginacion, TLB, vida de prestamos y pruebas de muerte del proceso.

## kernel/capabilities

Concede autoridad explicita y comprueba propietario, derechos y vigencia.

Estado: DISENO. Anillo: 0. Lenguaje: CASM.
Entrada: Peticion admitida y recursos con propietario.
Salida: Handle concedido, operacion comprobada o motivo de rechazo.
Depende de: Memoria y aislamiento (plan), Contratos de BMO-X2 (plan).
Aceptacion: Handle inventado, revocado o de otro proceso falla por su motivo; la autoridad no se hereda implicitamente.
Pendiente: Layout del handle, tabla, generacion, transferencia y revocacion.

## kernel/syscalls

Recibe operaciones de Ring 3 y comprueba el contrato antes de tocar recursos.

Estado: DISENO. Anillo: 0. Lenguaje: CASM.
Entrada: ABI versionado, registros, capability y buffers declarados.
Salida: Respuesta definida y retorno seguro a Ring 3.
Depende de: Capacidades (plan), Excepciones x86-64 (plan).
Aceptacion: Solicitud valida devuelve resultado; puntero/capacidad invalidos no comprometen al kernel.
Pendiente: Convencion de llamada, entradas/salidas, estados y primera operacion observable.

## userspace/runtime

Permite ejecutar un programa Rust aislado usando el ABI concedido por CASM.

Estado: DISENO. Anillo: 3. Lenguaje: Rust.
Entrada: Imagen admitida, pila, datos y ABI BMO-X2.
Salida: Entrada de usuario, llamadas y finalizacion/panico controlados.
Depende de: Puerta CASM/Rust (plan).
Aceptacion: Programa no_std entra en Ring 3, recibe respuesta del kernel y falla de forma contenida.
Pendiente: Target, entrada, enlace, wrappers del ABI y manejo de panico; aun no hay crate.

## userspace/services

Aloja servicios con autoridad concedida y politica fuera del kernel.

Estado: DISENO. Anillo: 3. Lenguaje: Rust.
Entrada: Runtime Rust y capacidades de sus recursos.
Salida: Operaciones de servicio con errores y limites definidos.
Depende de: Runtime minimo Rust (plan).
Aceptacion: La caida o revocacion de un servicio no concede acceso a recursos ajenos.
Pendiente: Primer servicio de diagnostico; entrada, disco y escritorio llegan por separado.

## userspace/apps

Ejercita los servicios y las capacidades con cargas visibles y repetibles.

Estado: DISENO. Anillo: 3. Lenguaje: Rust.
Entrada: Runtime y servicios concedidos.
Salida: Resultados de usuario y evidencia de fallos/permisos.
Depende de: Servicios Rust (plan).
Aceptacion: Primera app solicita una operacion, recibe respuesta y termina sin autoridad implicita.
Pendiente: Programa minimo antes de trasladar herramientas o aplicaciones mayores de BMO-X.

## tools

Valida el catalogo, construye metal64 y registra emision y verificacion reproducibles.

Estado: HOST. Anillo: host. Lenguaje: Python/PowerShell.
Entrada: Catalogo, semilla Clang, Python y fuentes locales.
Salida: Informes y compilaciones nuevas en build/; mapa persistente de SG.
Depende de: Entrada del compilador (codigo), Verificador metal64 (codigo), Banco metal64 (verificacion).
Aceptacion: Banco host y negativos del catalogo pasan; fallo de compilacion impide usar binario anterior.
Pendiente: Integrar despues taller Linux/QEMU y builds del kernel sin mezclar sus estados.

## heritage

Conserva los motivos de BMO-X y las huellas de los 38 originales CASM importados.

Estado: HOST. Anillo: contrato. Lenguaje: registro.
Entrada: Fuentes del mismo autor y commits fijados.
Salida: Manifest de origen, licencia y divergencias locales declaradas.
Depende de: contrato propio sin dependencias en este catalogo.
Aceptacion: Fuentes heredadas coinciden salvo adaptaciones nombradas; no se reetiqueta evidencia de otro proyecto.
Pendiente: Actualizar el registro de cambios cuando se amplie o reparta el compilador.

## docs

Ordena la construccion de CASM y del kernel por entregas que se puedan comprobar.

Estado: DISENO. Anillo: contrato. Lenguaje: plan.
Entrada: Contratos y evidencia actual de cada nodo.
Salida: Pasos C0..C11 con limites y aceptacion.
Depende de: Contratos de BMO-X2 (plan), Herencia y procedencia (plan).
Aceptacion: Ningun paso se cierra solo por tener carpetas, compilar o heredar resultados.
Pendiente: Cerrar C1 con el perfil estrategico x86-64 y ejecutar M1 de FIRST-BOOT en QEMU.

## CASM/traspaso

Conserva el intento de runtime/RDTSC con su verificador incompleto y limites escritos.

Estado: INVESTIGACION. Anillo: host. Lenguaje: C/Python parche.
Entrada: Parche de origen no aplicado y notas de traspaso.
Salida: Referencia para decidir la IR y las trampas del kernel.
Depende de: Lexico, sintaxis y semantica (plan), Codificador x86-64 (plan), Verificador metal64 (plan).
Aceptacion: Antes de aplicarlo: verify_runtime, pruebas por regla y ejecucion QEMU.
Pendiente: No es capacidad disponible ni entrega final de CASM.

## kernel/boot/entry.casm

Fuente propia minima que ejercita la emision de una entrada de kernel bajo el ABI metal64.

Estado: HOST. Anillo: 0. Lenguaje: CASM.
Entrada: Tabla de servicios metal64 del cargador, con metal_puts disponible.
Salida: Mensaje BMO-X2 y retorno al cargador; por ahora solo bytes verificados en host.
Depende de: Verificador metal64 (verificacion).
Aceptacion: HEX/IR y paquete coinciden con el contrato; la ejecucion de entrada se acredita por separado en QEMU.
Pendiente: No configura la CPU ni la memoria; falta cadena de carga, ejecucion observada y parada controlada.

## kernel/arch/x86_64/interrupts

Encamina IRQ con un contrato de entrada y reconocimiento separado de las excepciones.

Estado: DISENO. Anillo: 0. Lenguaje: CASM.
Entrada: CPU preparada, tabla de vectores y controlador de interrupciones identificado.
Salida: Evento acotado y retorno con el estado de CPU preservado.
Depende de: CPU x86-64 (plan), Excepciones x86-64 (plan).
Aceptacion: Interrupcion de prueba y fuente muda en QEMU; no perder ni repetir reconocimientos.
Pendiente: Controlador, vectores y politica de habilitacion antes de usar tiempo y dispositivos.

## kernel/init

Ordena fases y precondiciones del kernel sin esconder los fallos de un subsistema.

Estado: DISENO. Anillo: 0. Lenguaje: CASM.
Entrada: Contexto boot y resultados de CPU, excepciones y memoria.
Salida: Estado de fase listo o fallo con nombre y motivo.
Depende de: Excepciones x86-64 (plan), Memoria y aislamiento (plan).
Aceptacion: Una fase invalida impide ejecutar las siguientes; diagnostico identificable en QEMU.
Pendiente: Primera secuencia de inicializacion escrita en CASM despues de fijar el perfil de kernel.

## kernel/time

Ofrece tiempo monotono y plazos medibles antes de introducir planificacion.

Estado: DISENO. Anillo: 0. Lenguaje: CASM.
Entrada: Fuente de tiempo descubierta y mecanismo de interrupcion comprobado.
Salida: Lecturas y vencimientos con unidad y origen declarados.
Depende de: Interrupciones de hardware (plan).
Aceptacion: Plazo vence y tiempo no retrocede; frecuencia observada y coste de lectura registrados.
Pendiente: Elegir fuente y calibracion sin suponer frecuencias del Ryzen.

## kernel/sched

Gestiona ejecucion y espera con contexto y presupuesto definidos.

Estado: DISENO. Anillo: 0. Lenguaje: CASM.
Entrada: Tareas admitidas, memoria propia y fuente de tiempo.
Salida: Cambio de contexto o espera con estado preservado.
Depende de: Reloj y plazos (plan), Inicializacion del kernel (plan).
Aceptacion: Dos tareas no comparten contexto y una espera no gira en vacio; empezar por una CPU.
Pendiente: Modelo de tarea, registros preservados y despertares; SMP queda para otra entrega.

## kernel/ipc

Transporta mensajes y prestamos con autoridad y limites comprobados.

Estado: DISENO. Anillo: 0. Lenguaje: CASM.
Entrada: Procesos aislados, capacidades y buffers declarados.
Salida: Mensaje recibido o error de permisos, medida o vida util.
Depende de: Capacidades (plan).
Aceptacion: Rechaza destino ajeno, rango invalido y prestamo vencido sin filtrar memoria.
Pendiente: Primer canal y sus postcondiciones de cierre/muerte antes de servicios mayores.

## kernel/drivers

Aisla mecanismos de dispositivos del resto del kernel y explicita acceso a puertos/MMIO/DMA.

Estado: DISENO. Anillo: 0. Lenguaje: CASM.
Entrada: Hardware identificado, regiones concedidas e interrupciones comprobadas.
Salida: Operaciones acotadas con estado, tiempo limite y motivo de fallo.
Depende de: Memoria y aislamiento (plan), Interrupciones de hardware (plan).
Aceptacion: Aparato ausente o mudo no bloquea el kernel; permisos y DMA se prueban por separado.
Pendiente: Empezar con un dispositivo simple exigido por el arranque; no trasladar la investigacion GPU a esta base.

## CASM

Lenguaje y codificador propio x86-64: metal64, Native y su futura ampliacion privilegiada.

Estado: base HEREDADA; banco metal64 HOST. Ver STATUS-BMO-X2.md para los perfiles y limites.

## kernel

Futuro Ring 0 en CASM: arranque, CPU, excepciones, memoria, capacidades y puerta.

Estado: subsistemas en DISENO; boot/entry.casm es una sonda HOST, aun sin kernel arrancable.

## userspace

Futuro Ring 3 en Rust: runtime minimo, servicios y aplicaciones.

Estado: DISENO; aun sin crates y sin std del anfitrion.

## super-grafo

Mesa de trabajo: catalogo, notas, posiciones y fotografia real del analizador.

35 nodos del catalogo; relaciones de codigo y de plan distinguidas por clase.
