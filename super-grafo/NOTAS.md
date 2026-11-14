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
Depende de: Entrada y diagnosticos del frontend (codigo), Codificador x86-64 (codigo), IR y tipos metal64 (codigo), Frontend y emisor de parada (codigo).
Aceptacion: Casos HOST-READ, SOURCE-SIZE, HOST-WRITE y HOST-MEMORY donde el SO permite probarlo.
Pendiente: Portar el anfitrion del compilador propio cuando BMO-X2 tenga servicios de archivos.

## CASM/src/frontend.c

Valida el limite de fuente y despacha los rechazos reales de los modulos del frontend.

Estado: HOST. Anillo: host. Lenguaje: C semilla.
Entrada: Fuente acotada o regla, motivo y posicion del modulo que rechaza.
Salida: Llamada al parser o diagnostico estable legible por el Taller CASM.
Depende de: IR y tipos metal64 (codigo), Sintaxis metal64 (codigo), Interfaces del frontend (codigo).
Aceptacion: Los 333 casos diferenciales conservan bytes, IR, paquetes y diagnosticos.
Pendiente: Ampliar semantica de runtime y perfil de kernel; el reparto actual corresponde a metal64.

## CASM/src/casm.h

Contrato privado de IR con dos depositos compartidos acotados, sin buffers maximos por elemento.

Estado: HOST. Anillo: host. Lenguaje: C semilla.
Entrada: Declaraciones, expresiones y limites del perfil.
Salida: CasmProgram, CasmInteger, CasmConstant y CasmCall.
Depende de: contrato propio sin dependencias en este catalogo.
Aceptacion: Modelo de 361648 bytes; invariantes de almacenamiento y 333 casos coinciden con la base.
Pendiente: IR del kernel con flujo, funciones, efectos y trampas; la IR JSON metal64 conserva su formato.

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
Entrada: Modo largo y CPL0 entregados por el puente UEFI, con un paquete de entrada CASM verificado.
Salida: Primera entrada propia bajo 512 bytes, seguida por inicializacion y diagnostico del kernel.
Depende de: CASM para el metal privilegiado (plan), Contratos de BMO-X2 (plan), Primera entrada CASM (plan).
Aceptacion: Paquete menor de 512 bytes con cabecera incluida. QEMU confirma llegada y efecto en Ring 0.
Pendiente: Genesis y la parada propia tienen evidencia QEMU. Sigue el contexto propio y una excepcion controlada.

## kernel/arch/x86_64/cpu

Descubre capacidades CPU y prepara descriptores y estado privilegiado con limites explicitos.

Estado: DISENO. Anillo: 0. Lenguaje: CASM.
Entrada: Contrato de arranque y operaciones privilegiadas CASM.
Salida: Estado CPU apto para excepciones y aislamiento de Ring 3.
Depende de: Arranque del kernel (plan), Contexto de entrega (plan).
Aceptacion: CPUID y limites observados en QEMU; no se confunde el perfil del Ryzen con todo x86-64.
Pendiente: GDT/TSS, modos, registros de control y requisitos minimos del perfil inicial.

## kernel/arch/x86_64/exceptions

Contiene fallos de CPU y preserva el estado necesario para explicar quien fallo y donde.

Estado: DISENO. Anillo: 0. Lenguaje: CASM.
Entrada: CPU preparada y marcos de excepcion definidos.
Salida: Diagnostico, terminacion del proceso o parada controlada segun origen.
Depende de: CPU x86-64 (plan), Estado de CPU y cambio de contexto (plan), Pila inicial CASM (plan).
Aceptacion: #UD/#PF de Ring 3 terminan ese proceso; el kernel conserva control y evidencia.
Pendiente: La primera puerta #UD ya tiene evidencia. Faltan otros vectores, pilas de emergencia, diagnostico y contencion de Ring 3.

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
Depende de: Capacidades (plan), Excepciones x86-64 (plan), BEF2 y ABI de BMO-X (plan).
Aceptacion: Solicitud valida devuelve resultado; puntero/capacidad invalidos no comprometen al kernel.
Pendiente: Convencion de llamada, entradas/salidas, estados y primera operacion observable.

## userspace/runtime

Permite ejecutar un programa Rust aislado usando el ABI concedido por CASM.

Estado: DISENO. Anillo: 3. Lenguaje: Rust.
Entrada: Imagen admitida, pila, datos y ABI BMO-X2.
Salida: Entrada de usuario, llamadas y finalizacion/panico controlados.
Depende de: Puerta CASM/Rust (plan), BEF2 y ABI de BMO-X (plan), SBEF y congelacion del ABI (plan), Plan de herencia Ring 3 (plan).
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
Depende de: Entrada del compilador (codigo), Verificador metal64 (codigo), Banco metal64 (verificacion), Manifest de construccion (generacion), Generacion desde las listas (generacion), Espacio de trabajo BMO-X2 (codigo), Rutas host compatibles 5.1 y 7 (codigo).
Aceptacion: Banco metal64 y almacenamiento pasan; medir reconstruye la base y compara 333 fuentes sin ejecutar el destino.
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
Depende de: Entrada y diagnosticos del frontend (plan), Codificador x86-64 (plan), Verificador metal64 (plan).
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
Depende de: Reloj y plazos (plan), Inicializacion del kernel (plan), Proceso y ciclo de vida (plan).
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

## CASM/src/frontend/lexer.c

Reconoce tokens ASCII y posiciones sin interpretar los valores.

Estado: HOST. Anillo: host. Lenguaje: C11 semilla host.
Entrada: Fuente acotada y estado del parser.
Salida: Token, texto literal y posicion o rechazo preciso.
Depende de: Interfaces del frontend (codigo).
Aceptacion: Conserva limites de nombres, cadenas y comentarios en el banco y corpus diferencial.
Pendiente: Tokens y sintaxis adicionales del futuro perfil de kernel.

## CASM/src/frontend/symbols.c

Comprueba nombres reservados, declarados y tipos disponibles.

Estado: HOST. Anillo: host. Lenguaje: C11 semilla host.
Entrada: Identificador y tablas del programa.
Salida: Tipo o estado de nombre; nunca una declaracion implicita.
Depende de: Interfaces del frontend (codigo), Tipos de CPU metal64 (codigo).
Aceptacion: Duplicados, reservados, nombres ausentes y tipos conservan su rechazo.
Pendiente: Ambitos y simbolos de funciones al ampliar el perfil.

## CASM/src/frontend/integers.c

Evalua expresiones de constantes con anchura declarada y RPN comprobable.

Estado: HOST. Anillo: host. Lenguaje: C11 semilla host.
Entrada: Tokens, tipos y enteros ya declarados.
Salida: Valor exacto y RPN estable o rechazo de rango, profundidad o division.
Depende de: Interfaces del frontend (codigo), Nombres y tipos (codigo), Almacenamiento compartido (codigo).
Aceptacion: Extremos, negacion, referencias y corpus diferencial coinciden con la base.
Pendiente: Semantica de enteros en ejecucion del kernel.

## CASM/src/frontend/parser.c

Forma declaraciones, llamadas y la entrada del perfil metal64.

Estado: HOST. Anillo: host. Lenguaje: C11 semilla host.
Entrada: Tokens y reglas semanticas.
Salida: Programa admitido sin construcciones ignoradas.
Depende de: Lexico (codigo), Nombres y tipos (codigo), Enteros exactos (codigo), Almacenamiento compartido (codigo).
Aceptacion: Errores tardios y fuentes densas conservan orden y motivo de rechazo.
Pendiente: Gramatica explicita del perfil del kernel, sin mezclar silenciosamente Native.

## CASM/src/model/storage.c

Guarda datos y RPN en depositos comprobados dentro del modelo del anfitrion.

Estado: HOST. Anillo: host. Lenguaje: C11 semilla host.
Entrada: Programa en cero, direccion estable y escritura de la expresion actual.
Salida: Datos estables, uso acotado o rechazo antes de escribir.
Depende de: IR y tipos metal64 (codigo).
Aceptacion: Once invariantes; 68608 bytes de datos y 262272 de RPN bastan para la fuente admitida.
Pendiente: Medir RSS y tiempo real por separado; no atribuir esta medida a Ring 0.

## CASM/src/model/types.c

Tabla generada de nombres, anchuras y signo de los ocho tipos metal64.

Estado: HOST. Anillo: host. Lenguaje: C11 semilla host.
Entrada: CASM/catalog.json validado por catalog.py; tabla independiente del verificador.
Salida: Tabla unica compartida por simbolos, semantica y emisor.
Depende de: IR y tipos metal64 (codigo), Listas y jerarquia de CASM (generacion), Generacion desde las listas (generacion).
Aceptacion: La tabla generada esta vigente y sus anchuras y signos coinciden con el verificador independiente.
Pendiente: Tipos de runtime y layout del kernel.

## CASM/src/frontend/internal.h

Declara estado privado del parser, codigos de diagnostico e interfaces entre modulos.

Estado: HOST. Anillo: host. Lenguaje: C11 semilla host.
Entrada: Contrato del modelo y fronteras de responsabilidades.
Salida: Tipos y firmas del anfitrion, sin ABI del destino.
Depende de: IR y tipos metal64 (codigo).
Aceptacion: Todos los modulos compilan con avisos como errores; sus firmas no se duplican.
Pendiente: Mantener pequena esta interfaz al crecer el lenguaje.

## CASM/sources.json

Enumera las mismas fuentes y cabeceras x86-64 para Windows y Linux.

Estado: HOST. Anillo: host. Lenguaje: JSON host.
Entrada: Modulos reales del compilador.
Salida: Lista comun de compilacion y huellas que invalidan la cache.
Depende de: Entrada y diagnosticos del frontend (generacion), Lexico (generacion), Nombres y tipos (generacion), Enteros exactos (generacion), Sintaxis metal64 (generacion), Almacenamiento compartido (generacion), Tipos de CPU metal64 (generacion), Interfaces del frontend (generacion), Listas y jerarquia de CASM (generacion), Generacion desde las listas (generacion).
Aceptacion: Host y bootstrap usan este archivo; cambiar una cabecera invalida el registro.
Pendiente: Ejecucion del build y sanitizadores Linux en el taller.

## CASM/tests/workspace.c

Prueba extremos, estabilidad y rechazo sin escritura parcial del almacenamiento.

Estado: HOST. Anillo: host. Lenguaje: C11 semilla host.
Entrada: Modulo de almacenamiento y modelo.
Salida: Once comprobaciones y sizeof del modelo en el host.
Depende de: Almacenamiento compartido (verificacion).
Aceptacion: Pruebas de limite exacto y contadores invalidos pasan.
Pendiente: Acompanar cada cambio del deposito con casos de limite.

## CASM/tests/maturity.py

Reconstruye d2575a8 y exige la misma emision y diagnosticos del compilador reorganizado.

Estado: HOST. Anillo: host. Lenguaje: Python host.
Entrada: Clang host, historial Git y 333 fuentes deterministas.
Salida: Informe de modelo, ejecutables, casos identicos y limites de lo medido.
Depende de: Invariantes de memoria (verificacion), Entrada del compilador (verificacion), Verificador metal64 (verificacion).
Aceptacion: 279 fuentes aceptadas y 54 rechazadas coinciden; modelo baja 66.43 por ciento.
Pendiente: Medidas de RSS, ciclos y energia requieren experimentos propios.

## CASM/catalog.json

Define tipos, sintaxis, IR, codificaciones y capacidades por estado dentro de una jerarquia versionada.

Estado: HOST. Anillo: host. Lenguaje: JSON/Python host.
Entrada: Contrato metal64 actual y capacidades futuras declaradas.
Salida: Catalogo para el generador y SUPER GRAFO, sin convertir PLAN en instrucciones admitidas.
Depende de: contrato propio sin dependencias en este catalogo.
Aceptacion: Ocho pruebas de catalogo, tipos contra verificador independiente y codificaciones contra vector manual.
Pendiente: Ampliar el perfil solo junto a semantica, emisor, verificador y casos nuevos.

## CASM/catalog.py

Valida la jerarquia x86-64 y genera la tabla de tipos real del compilador.

Estado: HOST. Anillo: host. Lenguaje: JSON/Python host.
Entrada: catalog.json y tabla independiente INT_TYPES del verificador.
Salida: src/model/types.c generado antes de construir.
Depende de: Listas y jerarquia de CASM (codigo), Verificador metal64 (verificacion).
Aceptacion: Cambio de anchura incompatible, opcode alterado, ciclo o ruta externa impiden generar.
Pendiente: Generar otras tablas solo cuando su contrato y verificacion independiente esten definidos.

## CASM/tests/test_catalog.py

Exige que las listas no amplien silenciosamente lo que el compilador puede aceptar.

Estado: HOST. Anillo: host. Lenguaje: JSON/Python host.
Entrada: Catalogo valido y mutaciones independientes.
Salida: Ocho casos de aceptacion o rechazo con su motivo.
Depende de: Generacion desde las listas (verificacion), Listas y jerarquia de CASM (verificacion).
Aceptacion: El tipo generado coincide; arquitectura, estructura y bytes incorrectos se rechazan.
Pendiente: Agregar casos junto a cada nueva familia del perfil.

## BMO-X2.sg-workspace

Define la raiz portable y los valores iniciales de vista y panel de SUPER GRAFO.

Estado: HOST. Anillo: host. Lenguaje: JSON.
Entrada: Ruta del proyecto relativa al archivo; sesion local separada.
Salida: Apertura de BMO-X2 con grafo, Taller CASM y recuperacion de pestanas guardadas.
Depende de: Listas y jerarquia de CASM (plan).
Aceptacion: El lanzador abre la raiz real; guardar y reabrir conserva vista, panel y archivos sin ejecutar comandos.
Pendiente: Multiples raices y traslado de una sesion local entre computadoras.

## CASM/contracts/RING0.md

Fija el destino exclusivo del kernel y explica el vector de entrada sin atribuir privilegio al formato HEX.

Estado: HOST. Anillo: host. Lenguaje: contrato.
Entrada: Fuente congelada, IR, HEX y paquete del perfil metal64.
Salida: Contrato y lectura comprobable de los bytes actuales.
Depende de: CASM para el metal privilegiado (plan).
Aceptacion: Vector manual de entrada y rechazo de HEX o paquete alterado.
Pendiente: Operaciones propias privilegiadas y evidencia de ejecucion Ring 0.

## tools/hex_report.py

Repite el verificador y contrasta el paquete antes de mostrar linea, offsets, clase y bytes.

Estado: HOST. Anillo: host. Lenguaje: Python.
Entrada: Fuente congelada, IR, HEX y paquete del perfil metal64.
Salida: Contrato y lectura comprobable de los bytes actuales.
Depende de: Verificador metal64 (verificacion), Contrato CASM Ring 0 (plan).
Aceptacion: Vector manual de entrada y rechazo de HEX o paquete alterado.
Pendiente: Operaciones propias privilegiadas y evidencia de ejecucion Ring 0.

## kernel/boot/genesis

Contrato y fuente minima observable con salida mediante el cargador.

Estado: QEMU. Anillo: host. Lenguaje: contrato.
Entrada: Perfil metal64-0.2 y contratos de Genesis.
Salida: Fuente, vector HOST y ejecucion QEMU con siete casos comprobados.
Depende de: contrato propio sin dependencias en este catalogo.
Aceptacion: Siete casos QEMU aprobados: bytes exactos, framebuffer GENESIS, retorno CPL=0 y rechazos acotados; evidencia persistida.
Pendiente: Excepciones, memoria y mecanismos CASM propios; puente provisional heredado, sin kernel autonomo.

## kernel/boot/genesis/main.casm

Declara GENESIS, CR/LF y retorno; requiere la tabla de servicios metal64.

Estado: QEMU. Anillo: 0. Lenguaje: CASM.
Entrada: Perfil metal64-0.2 y contratos de Genesis.
Salida: 22 bytes comprobados y ejecutados mediante el puente provisional; paquete de 46 bytes.
Depende de: Genesis G0 y G1 (plan), Entrada y diagnosticos del frontend (plan), Puente UEFI provisional (plan).
Aceptacion: Siete casos QEMU aprobados: bytes exactos, framebuffer GENESIS, retorno CPL=0 y rechazos acotados; evidencia persistida.
Pendiente: Excepciones, memoria y mecanismos CASM propios; puente provisional heredado, sin kernel autonomo.

## kernel/boot/genesis/expected.hex

Fija 22 bytes independientes del emisor: 12 de instrucciones y 10 de datos.

Estado: HOST. Anillo: host. Lenguaje: contrato.
Entrada: Perfil metal64-0.2 y contratos de Genesis.
Salida: Fuente, vector o evidencia HOST del recorrido Genesis.
Depende de: contrato propio sin dependencias en este catalogo.
Aceptacion: 22 bytes de cuerpo, 46 de paquete; negativos rechazan alteraciones. Colores y motivos se conservan al guardar.
Pendiente: QEMU ya tiene evidencia; siguen pendientes mecanismos propios del kernel y prueba fisica.

## tools/genesis.py

Exige fuente congelada exacta, verificacion independiente, vector manual y paquete menor de 512 bytes.

Estado: HOST. Anillo: host. Lenguaje: contrato.
Entrada: Perfil metal64-0.2 y contratos de Genesis.
Salida: Fuente, vector o evidencia HOST del recorrido Genesis.
Depende de: Genesis: vector manual (verificacion), Genesis: fuente CASM (verificacion), Verificador metal64 (verificacion), Presupuesto de la entrada Ring 0 (verificacion).
Aceptacion: 22 bytes de cuerpo, 46 de paquete; negativos rechazan alteraciones. Colores y motivos se conservan al guardar.
Pendiente: QEMU ya tiene evidencia; siguen pendientes mecanismos propios del kernel y prueba fisica.

## super-grafo/genesis.json

Define posiciones y colores por responsabilidad, con un motivo visible por archivo.

Estado: HOST. Anillo: host. Lenguaje: contrato.
Entrada: Perfil metal64-0.2 y contratos de Genesis.
Salida: Fuente, vector o evidencia HOST del recorrido Genesis.
Depende de: Genesis G0 y G1 (plan).
Aceptacion: 22 bytes de cuerpo, 46 de paquete; negativos rechazan alteraciones. Colores y motivos se conservan al guardar.
Pendiente: QEMU ya tiene evidencia; siguen pendientes mecanismos propios del kernel y prueba fisica.

## kernel/boot/bridge

Bootstrap HEX manual importado de TALK-CPU; recibe firmware y entrega contexto metal64 al payload CASM.

Estado: HEREDADO. Anillo: host. Lenguaje: HEX heredado.
Entrada: Paquete Genesis comprobado, puente heredado y QEMU/OVMF.
Salida: Ejecucion o evidencia de la ruta provisional.
Depende de: contrato propio sin dependencias en este catalogo.
Aceptacion: Siete casos pasan y las huellas corresponden a esta fuente y paquete.
Pendiente: Arranque autonomo, excepciones y memoria propias; prueba fisica no realizada.

## docs/FIRST-BOOT.md

Ordena la prueba fisica del puente y la entrada CASM minima.

Estado: DISENO. Anillo: host. Lenguaje: contrato.
Entrada: EFI y paquete verificados, ruta separada en FAT32 y perfil UEFI x86-64.
Salida: Evidencia del firmware, entrada en CPL0 y parada controlada.
Depende de: Puente UEFI provisional (plan), Genesis: prueba aislada en QEMU (plan), Contexto de entrega (plan).
Aceptacion: El mismo EFI y paquete pasan QEMU y arrancan en el equipo; se observa la parada y Windows vuelve a arrancar.
Pendiente: El propietario observo gato y escritorio en el equipo. F2 y raton fisicos requieren entrada USB HID.

## tools/boot/wake.py

Prepara imagenes virtuales por run y registra entorno; nunca instala al PC.

Estado: HOST. Anillo: host. Lenguaje: herramienta/evidencia.
Entrada: Paquete Genesis comprobado, puente heredado y QEMU/OVMF.
Salida: Ejecucion o evidencia de la ruta provisional.
Depende de: Puente UEFI provisional (generacion), Genesis: guardian de bytes y tamano (verificacion).
Aceptacion: Siete casos pasan y las huellas corresponden a esta fuente y paquete.
Pendiente: Arranque autonomo, excepciones y memoria propias; prueba fisica no realizada.

## kernel/boot/genesis/evidence/qemu.json

Siete casos observados en QEMU: cuerpo cargado exacto, texto, CPL=0, retorno y rechazos.

Estado: QEMU. Anillo: host. Lenguaje: herramienta/evidencia.
Entrada: Paquete Genesis comprobado, puente heredado y QEMU/OVMF.
Salida: Ejecucion o evidencia de la ruta provisional.
Depende de: Genesis: prueba aislada en QEMU (verificacion), Genesis: fuente CASM (verificacion), Genesis G0 y G1 (verificacion).
Aceptacion: Siete casos pasan y las huellas corresponden a esta fuente y paquete.
Pendiente: Arranque autonomo, excepciones y memoria propias; prueba fisica no realizada.

## tools/paths.ps1

Forma nombres relativos para registrar huellas; rechaza rutas externas sin usar GetRelativePath de .NET Core.

Estado: HOST. Anillo: host. Lenguaje: PowerShell.
Entrada: Rutas absolutas de fuentes y raiz del proyecto.
Salida: Rutas relativas iguales entre versiones y evidencia de siete casos.
Depende de: contrato propio sin dependencias en este catalogo.
Aceptacion: Siete casos pasan en 5.1 y 7; despertar llega a QEMU con el mismo paquete.
Pendiente: Mantener la prueba de versiones al ampliar las herramientas del anfitrion.

## tools/tests/paths.ps1

Comprueba nombres con espacios, normalizacion y rechazos de rutas externas en Windows PowerShell 5.1 y PowerShell 7.

Estado: HOST. Anillo: host. Lenguaje: PowerShell.
Entrada: Rutas absolutas de fuentes y raiz del proyecto.
Salida: Rutas relativas iguales entre versiones y evidencia de siete casos.
Depende de: Rutas host compatibles 5.1 y 7 (verificacion).
Aceptacion: Siete casos pasan en 5.1 y 7; despertar llega a QEMU con el mismo paquete.
Pendiente: Mantener la prueba de versiones al ampliar las herramientas del anfitrion.

## CASM/profiles/ring0-stop.json

Define gramatica cerrada, entrada, efectos y bytes de ring0-stop-0.1.

Estado: HOST. Anillo: host. Lenguaje: CASM especificacion.
Entrada: Modo largo y CPL0 entregados por el cargador.
Salida: Contrato versionado para fuente, IR3 y terminal de 4 bytes.
Depende de: contrato propio sin dependencias en este catalogo.
Aceptacion: Solo kernel_main con cpu_halt; el perfil no se mezcla con metal64.
Pendiente: Ampliar contexto y excepciones con contrato y evidencia propios; no acredita kernel completo.

## kernel/boot/stop/main.casm

Ordena detener la CPU desde codigo propio.

Estado: QEMU. Anillo: 0. Lenguaje: CASM.
Entrada: Contrato ring0-stop-0.1.
Salida: CLI HLT JMP sin retorno ni servicios heredados.
Depende de: Contrato parada Ring 0 (verificacion).
Aceptacion: QEMU observa IF=0, HLT=1, CPL0 y RIP=entrada+2.
Pendiente: Ampliar contexto y excepciones con contrato y evidencia propios; no acredita kernel completo.

## CASM/src/kernel/stop.c

Analiza el terminal cerrado y emite IR3 y bytes propios.

Estado: HOST. Anillo: host. Lenguaje: C semilla.
Entrada: Fuente ASCII acotada con perfil explicito.
Salida: HEX de 4 bytes e IR con efectos y origen.
Depende de: Contrato parada Ring 0 (codigo), Lexico (codigo).
Aceptacion: Fuentes fuera de gramatica rechazan; metal64 conserva 333 casos.
Pendiente: Ampliar contexto y excepciones con contrato y evidencia propios; no acredita kernel completo.

## kernel/boot/stop/expected.hex

Fija la referencia independiente FA F4 EB FD.

Estado: HOST. Anillo: host. Lenguaje: vector x86-64.
Entrada: Contrato CLI HLT JMP rel8 -3.
Salida: Cuatro bytes de referencia.
Depende de: contrato propio sin dependencias en este catalogo.
Aceptacion: Emisor y verificador coinciden con el vector manual.
Pendiente: Ampliar contexto y excepciones con contrato y evidencia propios; no acredita kernel completo.

## CASM/stop_verify.py

Reconoce fuente, IR3 y bytes sin invocar el compilador.

Estado: HOST. Anillo: host. Lenguaje: Python control.
Entrada: Fuente congelada, HEX e IR.
Salida: Paquete FAGRAW64 de 28 bytes y mapa de tres instrucciones.
Depende de: Contrato parada Ring 0 (verificacion), Vector manual de parada (verificacion), Presupuesto de la entrada Ring 0 (verificacion).
Aceptacion: Mutaciones de cada bit, campos IR y fuente rechazan sin publicar.
Pendiente: Ampliar contexto y excepciones con contrato y evidencia propios; no acredita kernel completo.

## CASM/tests/test_stop.py

Prueba fronteras de gramatica, perfil, IR y emision.

Estado: HOST. Anillo: host. Lenguaje: Python control.
Entrada: Semilla construida desde sources.json.
Salida: Cuatro grupos de pruebas con mutaciones y rechazos.
Depende de: Frontend y emisor de parada (verificacion), Verificador independiente de parada (verificacion).
Aceptacion: No se admite RET, servicio, instruccion extra ni perfil distinto.
Pendiente: Ampliar contexto y excepciones con contrato y evidencia propios; no acredita kernel completo.

## kernel/boot/stop/evidence/qemu.json

Registra parada propia tras ExitBootServices y seis casos negativos.

Estado: QEMU. Anillo: host. Lenguaje: evidencia.
Entrada: Paquete verificado, puente heredado, QEMU y OVMF.
Salida: Siete casos con huellas, registros y captura.
Depende de: Fuente de parada propia (verificacion), Verificador independiente de parada (verificacion), Genesis: prueba aislada en QEMU (verificacion), Puente UEFI provisional (verificacion).
Aceptacion: No retorno; cuerpo exacto; RIP propio; IF=0; Ring 0 y HLT observados.
Pendiente: Ampliar contexto y excepciones con contrato y evidencia propios; no acredita kernel completo.

## contracts/ABI-BEF2.md

Conserva el formato y las dos puertas del padre como referencia para SBEF.

Estado: DISENO. Anillo: contrato. Lenguaje: contrato.
Entrada: Contrato BEF2 y ABI de BMO-X. Programas x86-64 de Rust, C y C++.
Salida: Referencia de campos, permisos y peticiones del padre.
Depende de: Contratos de BMO-X2 (plan).
Aceptacion: La revision de origen y sus archivos quedan identificados.
Pendiente: Comparar las decisiones del formato propio con esta referencia.

## CASM/entry_budget.py

Acota el paquete binario de la entrada a menos de 512 bytes.

Estado: HOST. Anillo: host. Lenguaje: Python control.
Entrada: Tamano verificado del cuerpo y del paquete FAGRAW64.
Salida: Cabecera, limite exclusivo y margen en bytes.
Depende de: contrato propio sin dependencias en este catalogo.
Aceptacion: 511 bytes caben, 512 se rechazan. La parada ocupa 28 bytes, con 483 de margen.
Pendiente: Medir el mismo presupuesto al ampliar la entrada con un contexto propio.

## contracts/SBEF.md

Define la evolucion de BEF2 para admitir programas x86-64 en BMO-X2.

Estado: DISENO. Anillo: contrato. Lenguaje: contrato.
Entrada: BEF2 de BMO-X, regiones del ejecutable y contrato de dos puertas.
Salida: Criterios del encabezado, admision, pruebas y versionado del ABI.
Depende de: BEF2 y ABI de BMO-X (plan), Memoria y aislamiento (plan).
Aceptacion: Dos lectores coinciden, QEMU prueba rechazo y aislamiento, y varios toolchains producen la misma peticion.
Pendiente: Cotejar cargador CASM con el prototipo HOST y probar INVOKE y WAIT antes de congelar.

## kernel/boot/context

Valida el contexto recibido y fija la pila inicial propia.

Estado: DISENO. Anillo: 0. Lenguaje: CASM.
Entrada: Modo largo, CPL0 y contexto del puente.
Salida: Contexto comprobado y pila acotada.
Depende de: Arranque del kernel (plan), Fuente de parada propia (plan).
Aceptacion: QEMU acredita pila propia y rechazo de un contexto invalido.
Pendiente: El perfil de pila ya prueba la entrega valida y RDI nulo. Faltan contrato propio de mapeos y guardas de pila.

## kernel/arch/x86_64/context

Prepara descriptores, TSS y estado de CPU que debe preservarse.

Estado: DISENO. Anillo: 0. Lenguaje: CASM.
Entrada: Capacidades de CPU, pila y contrato de contexto.
Salida: Marcos separados y estado preservado por tarea.
Depende de: CPU x86-64 (plan), Contexto de entrega (plan).
Aceptacion: QEMU comprueba pilas, registros y estado de CPU al cambiar de tarea.
Pendiente: Definir marcos y probar primero una CPU.

## kernel/diagnostics

Registra fases, excepciones y causa de parada.

Estado: DISENO. Anillo: 0. Lenguaje: CASM.
Entrada: Fase de inicializacion o marco de excepcion.
Salida: Registro acotado y decision de continuar, terminar proceso o parar.
Depende de: Excepciones x86-64 (plan).
Aceptacion: QEMU identifica excepcion, origen y fase sin depender del escritorio.
Pendiente: Emitir captura de excepcion y salida minima.

## kernel/mm/physical

Distingue memoria util, reservada y marcos asignados.

Estado: DISENO. Anillo: 0. Lenguaje: CASM.
Entrada: Mapa de arranque con limites verificados.
Salida: Asignacion y devolucion de marcos con propietario.
Depende de: Memoria y aislamiento (plan), Contexto de entrega (plan), Primer marco de RAM (plan), Propiedad y devolucion de un marco (plan).
Aceptacion: No asigna una reserva, detecta doble devolucion y recupera marcos al salir.
Pendiente: Generalizar el ciclo probado a multiples marcos y recuperar los recursos de un proceso.

## kernel/mm/virtual

Establece espacios virtuales separados y permisos por pagina.

Estado: DISENO. Anillo: 0. Lenguaje: CASM.
Entrada: Marcos fisicos, rangos y permiso solicitado.
Salida: Paginas de kernel y usuario con proteccion de escritura y ejecucion.
Depende de: Memoria fisica (plan), Tablas propias y alias de datos (plan), Revocacion en caliente y diario de fallos (verificacion).
Aceptacion: QEMU impide escritura de codigo y ejecucion de datos.
Pendiente: Probar fallos de permisos desde CPL3 y separar codigo RX de datos RW y NX.

## kernel/mm/user

Valida rangos y copia datos entre anillos.

Estado: DISENO. Anillo: 0. Lenguaje: CASM.
Entrada: Espacio de usuario, direccion, longitud y permiso requerido.
Salida: Copia acotada o error estable, con vida del rango controlada.
Depende de: Espacios y permisos (plan), Excepciones x86-64 (plan).
Aceptacion: Un rango ajeno, desbordado o con pagina ausente se rechaza.
Pendiente: Probar copia entre anillos y devolver paginas al asignador general.

## kernel/process

Crea contexto de usuario, entra en Ring 3 y recoge recursos al terminar.

Estado: DISENO. Anillo: 0. Lenguaje: CASM.
Entrada: Espacio aislado, imagen de prueba y pila.
Salida: Proceso con identidad y salida observable.
Depende de: Estado de CPU y cambio de contexto (plan), Memoria de usuario (plan), Inicializacion del kernel (plan), Fallo de proteccion desde CPL3 (plan).
Aceptacion: QEMU observa CPL3, retorno y fallo contenido, con recursos recuperados.
Pendiente: Arrancar una imagen SBEF y reutilizar recursos en un segundo proceso.

## kernel/loader

Admite y mapea una imagen SBEF bajo el contrato del proceso.

Estado: DISENO. Anillo: 0. Lenguaje: CASM.
Entrada: Bytes del ejecutable, limites, perfil SBEF y estado de CPU.
Salida: Imagen mapeada con entrada y permisos comprobados o motivo de rechazo.
Depende de: SBEF y congelacion del ABI (plan), Proceso y ciclo de vida (plan), Empaquetador ELF64 a SBEF (verificacion), Lector SBEF de referencia (verificacion), SBEF ABI 1 y llamadas desde CPL3 (verificacion), Contrato minimo del cargador SBEF (plan).
Aceptacion: El lector independiente y CASM coinciden en el vector de oro y rechazos, con QEMU en Ring 3.
Pendiente: La sonda LLVM en kernel/loader/external_sbef.S lee el SBEF entregado desde FAT32. Queda trasladar el cargador a CASM y asignar marcos y capacidades por proceso.

## kernel/syscalls/invoke

Despacha operaciones mediante capacidades del proceso activo.

Estado: DISENO. Anillo: 0. Lenguaje: CASM.
Entrada: Registros del ABI, handle, operacion y argumentos.
Salida: Estado y valor o rechazo acotado.
Depende de: Puerta CASM/Rust (plan), Proceso y ciclo de vida (plan), Memoria de usuario (plan), SBEF ABI 1 y llamadas desde CPL3 (verificacion).
Aceptacion: Operaciones autorizadas y denegadas dan el resultado esperado sin afectar otro proceso.
Pendiente: Generalizar capacidades por proceso y probar una operacion con buffer.

## kernel/syscalls/wait

Duerme y despierta tareas por senal o vencimiento.

Estado: DISENO. Anillo: 0. Lenguaje: CASM.
Entrada: Objeto esperable, secuencia y plazo.
Salida: Despertar, vencimiento o error con contexto preservado.
Depende de: Puerta CASM/Rust (plan), Planificacion (plan), Comunicacion entre procesos (plan), Proceso y ciclo de vida (plan), SBEF ABI 1 y llamadas desde CPL3 (verificacion).
Aceptacion: QEMU observa senal y plazo, sin espera activa ni perdida de un aviso concurrente.
Pendiente: El numero ya responde -4 en QEMU. Probar bloqueo, senal y plazo con dos tareas.

## kernel/security

Aplica procedencia y autoridad inicial a imagenes estructuralmente validas.

Estado: DISENO. Anillo: 0. Lenguaje: CASM.
Entrada: Imagen validada y politica de confianza.
Salida: Decision de ejecucion y capacidades iniciales acotadas.
Depende de: Cargador SBEF (plan), Capacidades (plan).
Aceptacion: Cambiar imagen o permiso invalida la admision correspondiente.
Pendiente: Definir confianza de produccion, integridad y revocacion.

## kernel/drivers/bus

Descubre recursos de dispositivos y delimita su acceso y DMA.

Estado: DISENO. Anillo: 0. Lenguaje: CASM.
Entrada: Perfil de plataforma y recursos descubiertos.
Salida: Recursos con propietario y transferencia controlada.
Depende de: Frontera de dispositivos (plan), Espacios y permisos (plan), Prestamo y revocacion DMA (plan).
Aceptacion: Un dispositivo de prueba queda limitado a sus recursos y ventanas DMA.
Pendiente: Elegir primer dispositivo y politica segun hardware medido.

## kernel/drivers/storage

Entrega bloques mediante un dispositivo acotado.

Estado: DISENO. Anillo: 0. Lenguaje: CASM.
Entrada: Dispositivo de bloques, rangos y capacidad.
Salida: Lecturas y errores de dispositivo reproducibles.
Depende de: Buses, recursos y DMA (plan).
Aceptacion: Lectura valida y fuera de rango en un disco virtual con imagen de prueba.
Pendiente: Separar los bloques del sistema de archivos.

## kernel/storage

Fija la frontera de acceso a imagenes y archivos sobre bloques.

Estado: DISENO. Anillo: 0. Lenguaje: CASM.
Entrada: Bloques, espacio de nombres y capacidad de directorio.
Salida: Acceso limitado a datos o imagen de proceso.
Depende de: Bloques y almacenamiento (plan), Capacidades (plan).
Aceptacion: Un servicio puede leer una imagen y rechaza una ruta fuera de su autoridad.
Pendiente: Elegir que mecanismo queda en CASM y que politica va a Ring 3.

## kernel/drivers/io

Ofrece recursos de entrada y salida a servicios autorizados.

Estado: DISENO. Anillo: 0. Lenguaje: CASM.
Entrada: Dispositivos descubiertos, buffers y eventos.
Salida: Canales y ventanas de aparato acotados.
Depende de: Buses, recursos y DMA (plan), Comunicacion entre procesos (plan).
Aceptacion: Pruebas de acceso, revocacion y fallo de servicio por dispositivo admitido.
Pendiente: QEMU verifica 260 informes de teclado y, en otra sonda, movimiento y foco con raton USB. Faltan uso simultaneo, reconexion y validacion en controladores fisicos.

## kernel/drivers/network

Expone colas y buffers de un dispositivo a un servicio autorizado.

Estado: DISENO. Anillo: 0. Lenguaje: CASM.
Entrada: Dispositivo, memoria asignada y permisos.
Salida: Transporte acotado de tramas para Ring 3.
Depende de: Buses, recursos y DMA (plan), Comunicacion entre procesos (plan).
Aceptacion: Prueba de envio, recepcion y aislamiento con dispositivo virtual.
Pendiente: Elegir dispositivo y dejar protocolos en el servicio.

## kernel/arch/x86_64/smp

Extiende el contexto por CPU y coordina acceso concurrente.

Estado: DISENO. Anillo: 0. Lenguaje: CASM.
Entrada: Base estable de una CPU, topologia y requisitos del equipo.
Salida: CPU adicionales, sincronizacion y registro por CPU.
Depende de: Planificacion (plan), Estado de CPU y cambio de contexto (plan), Espacios y permisos (plan).
Aceptacion: QEMU con varias CPU conserva estado y permisos antes de probar metal.
Pendiente: Definir invariantes de sincronizacion y perfil de hardware.

## docs/RING0-PLAN.md

Define la evidencia necesaria para congelar SBEF y el ABI.

Estado: DISENO. Anillo: contrato. Lenguaje: contrato.
Entrada: Emision CASM, aislamiento, cargador, capacidades y dos puertas.
Salida: Contrato congelable con casos de oro, rechazos y medidas.
Depende de: Presupuesto de la entrada Ring 0 (plan), Diagnostico y recuperacion (plan), Cargador SBEF (plan), Puerta INVOKE (plan), Puerta WAIT (plan), Politica de admision (plan).
Aceptacion: QEMU prueba carga, aislamiento, INVOKE y WAIT y coinciden varios toolchains.
Pendiente: Cerrar primero contexto, pila y excepcion.

## heritage/RING3-TRANSFER.md

Ordena la transferencia de Ultra_userspace por dependencia real.

Estado: DISENO. Anillo: contrato. Lenguaje: contrato.
Entrada: Revision del padre, ABI y SBEF validados, requisitos de cada componente.
Salida: Orden de traslado, compatibilidad y evidencia por componente.
Depende de: Cierre de la base Ring 0 (plan).
Aceptacion: El runtime Rust y un programa COBOL empaquetados en SBEF obtienen el mismo resultado por el ABI. Cada servicio prueba sus capacidades y recuperacion.
Pendiente: Empezar por runtime una vez cerrada la base.

## kernel/arch/x86_64/cpu/identify.casm

Descubre fabricante y hoja basica maxima con CPUID hoja 0.

Estado: QEMU. Anillo: 0. Lenguaje: CASM.
Entrada: CPU x86-64 en modo largo y CPL0 tras el puente.
Salida: Registros CPUID preservados en la parada de 8 bytes.
Depende de: CPU x86-64 (codigo), Verificador independiente de parada (verificacion).
Aceptacion: Dos modelos QEMU ejecutan el mismo HEX y reportan sus valores propios.
Pendiente: Ampliar hojas segun lo que necesita la inicializacion.

## tools/boot/cpu_config.py

Contrasta imagen y resultado antes de publicar profile.config.

Estado: HOST. Anillo: host. Lenguaje: Python control.
Entrada: Paquete, evidencia QEMU y registros de la CPU invitada.
Salida: Configuracion acotada y vinculada al paquete.
Depende de: Identificacion CPUID (verificacion), Genesis: prueba aislada en QEMU (verificacion).
Aceptacion: Rechaza registros ausentes, valores invalidos y resultados que no coinciden.
Pendiente: El kernel debe consumir capacidades validadas antes de aplicar opciones.

## kernel/arch/x86_64/cpu/evidence.json

Vincula dos perfiles observados al mismo paquete verificado.

Estado: QEMU. Anillo: host. Lenguaje: evidencia.
Entrada: Ejecuciones QEMU con qemu64 y Nehalem.
Salida: Huella del paquete, registros, informes y configuraciones de ambos modelos.
Depende de: Guardian del perfil observado (verificacion).
Aceptacion: Mismo paquete con fabricante y hoja basica maxima distintos segun la CPU invitada.
Pendiente: kernel/arch/x86_64/cpu/cache_profile.inc registra la L1 del CPU de arranque. Queda probar deteccion por nucleo y mediciones en hardware.

## kernel/boot/context/main.casm

Comprueba la entrega y activa una pagina de pila en una reserva del puente.

Estado: QEMU. Anillo: 0. Lenguaje: CASM.
Entrada: RDI, RBP, reserva del puente y ExitBootServices completado.
Salida: RSP alineado y resultado de la comprobacion. Rechazo sin cambiar de pila.
Depende de: Contexto de entrega (codigo), Verificador independiente de parada (verificacion).
Aceptacion: QEMU observa PUSH y POP en la pagina propia y rechazo con RDI nulo.
Pendiente: Usar un contexto propio con permisos y pagina de guarda. Instalar IDT para la primera excepcion.

## kernel/boot/splash/main.casm

Dibuja y anima el gato en el framebuffer entregado al Ring 0.

Estado: QEMU. Anillo: 0. Lenguaje: CASM.
Entrada: Fuente de 32 filas y framebuffer valido tras ExitBootServices.
Salida: Tres cuadros y parada propia en un paquete de 508 bytes.
Depende de: Puente UEFI provisional (plan), Guardian del HEX grafico (verificacion).
Aceptacion: QEMU verifica 3 cuadros pixel por pixel y parada en CPL0.
Pendiente: Integrar el diagnostico grafico despues de validar tablas y excepciones.

## CASM/splash_verify.py

Reconstruye mascara y verifica el renderer, IR y presupuesto.

Estado: HOST. Anillo: host. Lenguaje: Python control.
Entrada: Fuente congelada, HEX, IR y vector del renderer.
Salida: Paquete FAGRAW64 de 508 bytes y mapa de codigo y datos.
Depende de: Presupuesto de la entrada Ring 0 (verificacion).
Aceptacion: Rechaza ancho incorrecto, instrucciones y mascara alteradas.
Pendiente: Ampliar solo con un contrato de dibujo y evidencia equivalente.

## kernel/boot/splash/evidence/qemu.json

Vincula la animacion observada al paquete exacto y al entorno QEMU.

Estado: QEMU. Anillo: host. Lenguaje: evidencia.
Entrada: Tres capturas del framebuffer, informe y paquete verificado.
Salida: Huellas, registros de la prueba y repeticion visual.
Depende de: Gato animado de arranque (verificacion).
Aceptacion: Tres cuadros comparados pixel a pixel con 1024 MiB de RAM virtual.
Pendiente: Integrar la escena con diagnostico del kernel antes de pruebas fisicas.

## contracts/FAGGIN.md

Define la convergencia de reset y UEFI en una entrega CASM x86-64.

Estado: DISENO. Anillo: contrato. Lenguaje: contrato.
Entrada: Contratos de CPU y referencias BMO-X y TALK-CPU.
Salida: Fronteras por modo, evidencia exigida y ABI de entrega.
Depende de: Contratos de BMO-X2 (plan).
Aceptacion: Se observa cada transicion en QEMU y ambas rutas entregan el contrato de entrada.
Pendiente: Emitir y verificar las etapas propias desde reset.

## kernel/boot/faggin/stage16

Prepara el primer salto desde reset en la ruta propia.

Estado: DISENO. Anillo: contrato. Lenguaje: CASM arranque.
Entrada: Estado de reset, ROM y espacio de pila temporal.
Salida: A20, GDT y entrada protegida de 32 bits.
Depende de: Rutas de arranque Faggin (plan).
Aceptacion: QEMU registra el cambio de modo y el destino del salto.
Pendiente: Definir el formato y la emision CASM de la etapa de 16 bits.

## kernel/boot/faggin/stage32

Prepara segmentos, pila y paginacion inicial para modo largo.

Estado: DISENO. Anillo: 0. Lenguaje: CASM.
Entrada: Entrega protegida de 32 bits y memoria reservada.
Salida: Tablas y salto al segmento de codigo de 64 bits.
Depende de: Faggin 16 bits (plan).
Aceptacion: QEMU verifica registros de control y rangos de las reservas.
Pendiente: Emitir la transicion de 32 a 64 bits con vector independiente.

## kernel/boot/faggin/stage64

Entrega contexto x86-64 a la misma entrada que utiliza UEFI.

Estado: DISENO. Anillo: 0. Lenguaje: CASM.
Entrada: Modo largo y mapa inicial de la ruta reset.
Salida: Contexto, pila y recursos de arranque comprobables.
Depende de: Faggin 32 bits (plan), Contexto de entrega (plan).
Aceptacion: La entrada CASM observa modo largo y registra una excepcion controlada.
Pendiente: Unir con la entrada despues de validar la IDT propia.

## kernel/boot/splash/hd/main.casm

Dibuja la silueta de 64 celdas por lado con tres intensidades de ojos.

Estado: QEMU. Anillo: 0. Lenguaje: CASM.
Entrada: Mascara derivada de BMO-X y framebuffer entregado por UEFI.
Salida: Tres cuadros de 256 por 256 y paquete de demostracion de 1279 bytes.
Depende de: Gato animado de arranque (verificacion), Guardian del HEX grafico (verificacion).
Aceptacion: QEMU compara cada cuadro y confirma la parada de Ring 0.
Pendiente: Integrar la escena con el diagnostico del kernel.

## kernel/arch/x86_64/exceptions/main.casm

Instala una IDT minima y registra el vector y RIP de una excepcion controlada.

Estado: QEMU. Anillo: 0. Lenguaje: CASM.
Entrada: Entrega x86-64 valida y memoria reservada por el puente.
Salida: Vector 6, RIP de UD2 y parada propia, o rechazo de entrega.
Depende de: Excepciones x86-64 (plan), Verificador independiente de parada (verificacion).
Aceptacion: QEMU coteja IDTR, puerta, marco en RAM y rechazo con RDI nulo.
Pendiente: Generalizar excepciones y diagnostico antes de aislar un proceso.

## kernel/mm/physical/main.casm

Prueba escritura y lectura de un marco convencional tras ExitBootServices.

Estado: QEMU. Anillo: 0. Lenguaje: CASM.
Entrada: Entrega del puente, mapa UEFI y rango de 256 MiB de la VM.
Salida: Marca de ocho bytes en un marco de 4096 bytes y parada en CPL0.
Depende de: Contexto de entrega (codigo), Verificador independiente de parada (verificacion).
Aceptacion: QEMU coteja el mapa, la direccion y la marca; rechaza RDI nulo.
Pendiente: Integrar el marco en un asignador con propiedad y liberar recursos.

## tools/boot/memory_capture.py

Comprueba la primera direccion elegible, la marca fisica y el contexto.

Estado: HOST. Anillo: host. Lenguaje: Python control.
Entrada: Registros, mapa de memoria y lectura fisica de QEMU.
Salida: Evidencia por caso y bytes convencionales observados.
Depende de: Primer marco de RAM (verificacion).
Aceptacion: Coteja entrega valida e invalida en qemu64 y Nehalem.
Pendiente: Extender la prueba al ciclo de asignacion y devolucion.

## tools/boot/weights.py

Mide artefactos en disco y lee la RAM configurada de cada VM.

Estado: HOST. Anillo: host. Lenguaje: Python control.
Entrada: Ultima prueba aprobada por perfil y huella del paquete.
Salida: Bytes de HEX, codigo, paquete, puente, imagenes y directorio de prueba.
Depende de: Guardian QEMU del marco (verificacion).
Aceptacion: Mide archivos conservados y descarta pruebas incompletas.
Pendiente: Medir memoria residente del kernel cuando exista un asignador.

## kernel/mm/physical/lifecycle/main.casm

Asigna, protege la propiedad, borra y reasigna un marco de 4 KiB.

Estado: QEMU. Anillo: 0. Lenguaje: CASM.
Entrada: Mapa de arranque y dos propietarios de prueba.
Salida: Estado de seis pasos, propietario final y marco limpio.
Depende de: Primer marco de RAM (codigo), Guardian QEMU del marco (verificacion).
Aceptacion: QEMU coteja agotamiento, devolucion ajena, doble devolucion y 4096 bytes borrados.
Pendiente: Administrar devolucion y propiedad de multiples marcos.

## kernel/mm/virtual/main.casm

Instala CR3 propio y separa el mapa supervisor de un alias de usuario.

Estado: QEMU. Anillo: 0. Lenguaje: CASM.
Entrada: Mapa UEFI y seis marcos convencionales contiguos.
Salida: Cinco tablas y una pagina de datos de solo lectura y NX.
Depende de: Primer marco de RAM (codigo), Verificador independiente de parada (verificacion).
Aceptacion: QEMU coteja las entradas, CR3 activo, NX, WP y la lectura por el alias.
Pendiente: Generalizar los espacios por proceso y sus permisos.

## kernel/mm/user/main.casm

Ejecuta un programa fijo en CPL3 y captura el acceso prohibido en Ring 0.

Estado: QEMU. Anillo: 0. Lenguaje: CASM.
Entrada: Tablas, GDT, TSS, puerta 14 y programa de prueba.
Salida: Marco hardware de #PF y dos paginas de usuario desmapeadas y borradas.
Depende de: Tablas propias y alias de datos (plan), Primera excepcion #UD (plan).
Aceptacion: QEMU comprueba CPL3, CR2, error 5, pila de Ring 0 y memoria a cero.
Pendiente: Reutilizar los marcos con el asignador general y ejecutar un segundo proceso.

## tools/host

Coordina la inspeccion, admision, diagnostico y publicacion de ejecutables x86-64.

Estado: HOST. Anillo: host. Lenguaje: Python control.
Entrada: ELF64 o PE32+ enlazado y version de ABI.
Salida: SBEF admitido, comparacion de builds por archivo y paginas, o rechazo con campo y offset.
Depende de: Empaquetador ELF64 a SBEF (codigo), Lector SBEF de referencia (codigo), Inspeccion PE32+ (codigo).
Aceptacion: El vector ELF conserva sus bytes, pack exige los presupuestos y compare distingue bytes de archivo de paginas mapeadas.
Pendiente: Ejecutar el cliente comun de varios productores y admitir PE32+ freestanding.

## tools/host/importers/elf.py

Convierte segmentos de un ELF64 estatico a regiones SBEF comprobadas.

Estado: HOST. Anillo: host. Lenguaje: Python control.
Entrada: Ejecutable x86-64 freestanding y contrato binario provisional.
Salida: Cabecera, tabla de regiones y bytes de la imagen SBEF.
Depende de: SBEF y congelacion del ABI (codigo), Lector SBEF de referencia (verificacion).
Aceptacion: Vector fijo y rechazos de truncado, solape, permisos y entrada; pruebas C y C++.
Pendiente: Cotejar la admision general contra el cargador CASM. El escritorio Rust ya usa ELF64 y SBEF.

## tools/host/sbef/format.py

Valida la imagen SBEF y localiza el campo rechazado.

Estado: HOST. Anillo: host. Lenguaje: Python control.
Entrada: Bytes SBEF y contrato provisional.
Salida: Regiones admitidas o codigo, campo, offset e indice.
Depende de: contrato propio sin dependencias en este catalogo.
Aceptacion: Coteja el vector y rechaza permisos, truncado y solapes.
Pendiente: Compartir vectores de admision y diagnostico con CASM.

## tools/host/importers/pe.py

Expone secciones y directorios PE que requieren adaptacion de ABI.

Estado: HOST. Anillo: host. Lenguaje: Python control.
Entrada: Ejecutable PE32+ x86-64.
Salida: Inventario HOST y motivos que impiden empaquetar.
Depende de: contrato propio sin dependencias en este catalogo.
Aceptacion: Muestra importaciones, TLS y reubicaciones cuando estan declarados.
Pendiente: Implementar y probar un perfil PE freestanding para conversion.

## userspace/supervisor

Ordena, configura y recupera servicios desde CPL3.

Estado: DISENO. Anillo: 3. Lenguaje: Rust.
Entrada: Proceso Rust admitido, runtime y capacidades concedidas.
Salida: Servicios iniciados, vigilados y recuperados con autoridad acotada.
Depende de: Servicios Rust (plan), Runtime minimo Rust (plan), Inventario de crates de BMO-X (plan), Reglas de jerarquia de Ring 3 (plan).
Aceptacion: Reinicia un servicio caido sin elevar privilegio ni heredar autoridad implicita.
Pendiente: Implementar despues de arrancar SBEF y verificar INVOKE y WAIT.

## kernel/syscalls/main.casm

Valida SBEF embebido y ejecuta tres entradas SYSCALL.

Estado: QEMU. Anillo: 0. Lenguaje: CASM.
Entrada: Una region SBEF RX, contexto y CPU con SYSCALL.
Salida: Echo, capacidad rechazada, estado WAIT y limpieza de usuario.
Depende de: Fallo de proteccion desde CPL3 (plan).
Aceptacion: QEMU ejecuta CPL3 y rechaza ABI ajeno o W+X antes de copiar.
Pendiente: Cargar imagen externa y probar WAIT con senal y plazo.

## tools/host/toolchains/abi.py

Construye un cliente comun y coteja los bytes de los stubs ELF.

Estado: QEMU. Anillo: host. Lenguaje: Python control.
Entrada: Cliente C, cabecera ABI 1, compilador y vector HEX.
Salida: SBEF para ELF o inventario de un objeto COFF MSVC.
Depende de: HOST: del ejecutable a SBEF (verificacion), Empaquetador ELF64 a SBEF (generacion).
Aceptacion: GCC C, Clang C/C++ y Rust verifican INVOKE, WAIT y limpieza tras fallo en QEMU en un paquete de hasta 2048 bytes. MSVC se inspecciona como COFF.
Pendiente: El reuso de dos paginas entre dos SBEF pasa en QEMU. Faltan cargador externo general, revocacion por proceso y PE32+ freestanding.

## kernel/mm/virtual/revoke/main.casm

Retira una pagina, invalida la traduccion y reanuda CPL3.

Estado: QEMU. Anillo: 0. Lenguaje: CASM.
Entrada: Pagina de datos usada desde CPL3 y un fallo de proteccion.
Salida: Dos registros de fallo y tres marcos de usuario borrados.
Depende de: Fallo de proteccion desde CPL3 (plan).
Aceptacion: QEMU distingue supervisor de pagina revocada y coteja la memoria.
Pendiente: Integrar propietarios, referencias compartidas y confirmacion SMP.

## contracts/SBEF-LOADER.md

Separa admision, plan de carga, memoria y diagnostico.

Estado: DISENO. Anillo: contrato. Lenguaje: contrato.
Entrada: SBEF y ABI, limites del proceso y copia inmutable.
Salida: Plan de rangos y permisos o rechazo con ubicacion.
Depende de: contrato propio sin dependencias en este catalogo.
Aceptacion: Una imagen externa llega a CPL3; un fallo revierte reservas parciales.
Pendiente: Aplicar el contrato a un SBEF producido por LLVM.

## heritage/RING3-CRATES.md

Agrupa crates del padre por familia y dependencias declaradas.

Estado: HOST. Anillo: host. Lenguaje: inventario.
Entrada: Manifiestos Cargo del commit fijado de BMO-X.
Salida: Inventario de transferencia y dependencias directas del ABI.
Depende de: contrato propio sin dependencias en este catalogo.
Aceptacion: Regenerar el inventario desde Git y obtener el mismo documento.
Pendiente: Validar cierre transitivo, build y pruebas de capacidades.

## userspace/POLICY.md

Separa runtime, supervisor, servicios y aplicaciones mediante capacidades.

Estado: DISENO. Anillo: contrato. Lenguaje: contrato.
Entrada: SBEF admitido, ABI, dependencias y autoridad explicita.
Salida: Orden de arranque y criterios de admision de componentes.
Depende de: contrato propio sin dependencias en este catalogo.
Aceptacion: Un cliente y un interprete actuan solo con capacidades concedidas.
Pendiente: Probar procesos externos y aplicar la politica al primer servicio.

## Ultra-J/FORMAT.md

Fija bytes de instrucciones, estilo por clase y cierre de regiones.

Estado: HOST. Anillo: contrato. Lenguaje: contrato.
Entrada: Objetos de interfaz y reglas de propiedad.
Salida: Formatos UJBC y UJTH para el runtime de usuario.
Depende de: contrato propio sin dependencias en este catalogo.
Aceptacion: Los vectores manuales cargan con longitudes exactas y estilos acotados.
Pendiente: Ampliar UJBC v2 con campos y metodos definidos por el usuario.

## Ultra-J/runtime.py

Verifica los dos archivos y ejecuta la recuperacion por region en HOST.

Estado: HOST. Anillo: host. Lenguaje: Python.
Entrada: Bytecode UJBC y tema UJTH.
Salida: Rechazo con offset o informe de objetos, estilos y bytes recuperados.
Depende de: ULTRA-J: bytecode y tema (verificacion), Escritorio y espacios de trabajo (plan).
Aceptacion: Recuperar 64 bytes en un cierre y reutilizar el offset cero.
Pendiente: Integrar VM SBEF y presentar el tema en DIRECTOR bajo QEMU.

## Ultra-J/compiler.py

Traduce el perfil de clases y regiones a instrucciones UJBC verificadas.

Estado: HOST. Anillo: host. Lenguaje: Python.
Entrada: Fuente .uj con sintaxis estilo Java.
Salida: Binario .ujb reproducible o error con offset del fuente.
Depende de: ULTRA-J: verificador y reciclador (codigo).
Aceptacion: El ejemplo v1 conserva su vector manual y v2 verifica el receptor y su metodo.
Pendiente: Agregar metodos de usuario, control de flujo y buffers para el autocompilador.

## Ultra-J/view.py

Compila estructura y estilos a dos listas binarias de dibujo.

Estado: QEMU. Anillo: host. Lenguaje: Python.
Entrada: Vista .ujh, estilos .ujc y atlas de CABINA.
Salida: Vista UJVI con coordenadas logicas independiente del destino.
Depende de: ULTRA-J: bytecode y tema (plan).
Aceptacion: QEMU verifica ambos estados, la accion con Enter, el reinicio con Esc y el rechazo de SBEF W+X.
Pendiente: Conectar eventos por elemento y compositor DIRECTOR.

## Ultra-J/package.py

Resuelve estilos y crates invocados por la estructura del paquete.

Estado: HOST. Anillo: host. Lenguaje: Python.
Entrada: Carpeta con accion, vista y dependencias locales versionadas.
Salida: UJBC, UJVI y grafo JSON o diagnostico con archivo y contexto.
Depende de: ULTRA-J: compilador inicial (codigo), ULTRA-J: estructura y estilos (codigo).
Aceptacion: Compila solo los crates invocados, reporta su llamada y rechaza ciclos.
Pendiente: Extender el argumento de region a valores de ejecucion y tipos exportados.

## Ultra-J/targets/x86_64

Empaqueta un presentador de Ring 3 para los servicios INVOKE y WAIT de BMO-X2.

Estado: QEMU. Anillo: host. Lenguaje: ASM x86-64 y PowerShell.
Entrada: Vista UJVI compilada y ABI x86-64.
Salida: SBEF con presentador nativo, vista y accion UJBC de solo lectura.
Depende de: ULTRA-J: estructura y estilos (codigo).
Aceptacion: La accion del boton cambia la vista y su arena queda a cero en QEMU.
Pendiente: Cargar UJBC separado en una VM general, integrar DIRECTOR y comprobar en metal.

## userspace/services/desktop

Compone superficies y gestiona ventanas y cuatro espacios inspirados en Ultra-LinuX.

Estado: QEMU. Anillo: 3. Lenguaje: Rust.
Entrada: Eventos de entrada, superficies de clientes y capacidad de pantalla.
Salida: Cuadro en RAM, espacio activo, foco, movimiento de ventanas y peticion de cierre desde CABINA.
Depende de: Supervisor Rust de Ring 3 (plan), Mezcla y controles de audio (plan).
Aceptacion: HOST exige presupuesto SBEF y puerta de sesion de hasta 2048 bytes. QEMU registra L1 por CPUID y verifica arranque FAT32, entrada, rechazo de permisos y reuso de cinco marcos.
Pendiente: Entregar marcos al asignador, cargar un SBEF distinto, aislar procesos y conectar el compositor y el planificador.

## userspace/services/desktop/src/keyboard.rs

Convierte eventos de BMO-X en cambios de espacio, foco numerado y movimiento de ventanas.

Estado: HOST. Anillo: 3. Lenguaje: Rust.
Entrada: Scancode normalizado, flanco y modificadores asociados al evento.
Salida: Atajo consumido o evento para el componente enfocado.
Depende de: Escritorio y espacios de trabajo (codigo), Entrada, pantalla y audio (plan).
Aceptacion: HOST verifica cambio de espacio, movimiento, repeticion, liberacion y reenvio.
Pendiente: Conectar la capacidad de entrada y probar teclado real en QEMU.

## userspace/services/desktop/src/usb_hid.rs

Traduce informes USB boot en flancos de teclado, movimiento y botones del raton.

Estado: HOST. Anillo: 3. Lenguaje: Rust.
Entrada: Informes de endpoints HID con protocolo boot seleccionado.
Salida: Eventos para atajos, cliente enfocado y puntero.
Depende de: Teclado y atajos del escritorio (codigo), Entrada, pantalla y audio (plan).
Aceptacion: HOST comprueba Ctrl Super 2, F2, deltas con signo, rollover y liberacion al desconectar.
Pendiente: Conectar el transporte xHCI y probar perifericos USB en QEMU y hardware.

## tools/build-doom-probe.ps1

Compila la aritmetica original de DoomGeneric y empaqueta un cliente ELF64.

Estado: QEMU. Anillo: host. Lenguaje: PowerShell y C.
Entrada: m_fixed.c fijado, toolchain x86-64 ELF y portal ABI 1.
Salida: Tabla ELF, doom-fixed.sbef e informe QEMU de ejecucion CPL3.
Depende de: Contrato minimo del cargador SBEF (plan), Empaquetador ELF64 a SBEF (generacion).
Aceptacion: QEMU comprueba tres cuadros HD y despues el SBEF de GCC, tres syscalls y borrado.
Pendiente: Generalizar el cargador externo CASM fuera de las sondas.

## tools/build-doom-engine.ps1

Enlaza DoomGeneric con el runtime C y presenta el juego por CPU.

Estado: QEMU. Anillo: host. Lenguaje: PowerShell y C.
Entrada: 80 unidades GCC, ABI 1 experimental e IWAD local de solo lectura.
Salida: ELF64 estatico, doom-engine.sbef y capturas de E1M1 en QEMU.
Depende de: Sonda DOOM C a SBEF (verificacion), Empaquetador ELF64 a SBEF (generacion).
Aceptacion: CPL3, mapa RX/R/RW con NX, doom run desde CABINA, pantalla completa, movimiento relativo PS/2, cambios de foco y espacio, cierre con Super + Q y rechazo W+X.
Pendiente: Proceso SBEF independiente, lectura de disco invitado, guardado, audio y entrada USB continua.

## userspace/services/audio

Mezcla PCM estereo de hasta dieciseis fuentes con ganancia acotada.

Estado: HOST. Anillo: 3. Lenguaje: Rust.
Entrada: Bloques PCM, ganancias por canal y volumen general.
Salida: PCM mezclado, picos por canal y contador de saturacion.
Depende de: Entrada, pantalla y audio (plan), Prestamo y revocacion DMA (plan).
Aceptacion: HOST verifica balance, silencio, recorte y picos WAV. El monitor QEMU enumera Intel HDA y su codec.
Pendiente: Reproducir desde el invitado, conectar DMA, panel y fuentes de DOOM.

## kernel/drivers/bus/DMA.md

Acota los marcos visibles al dispositivo y controla su devolucion.

Estado: DISENO. Anillo: contrato. Lenguaje: contrato.
Entrada: Dominio IOMMU, dispositivo, capacidad y rango.
Salida: Transferencia autorizada o rechazo con fase de diagnostico.
Depende de: Revocacion en caliente y diario de fallos (plan).
Aceptacion: QEMU limita DMA al buffer y retiene el marco si falta confirmacion.
Pendiente: Implementar la cola y probar el primer dispositivo virtual.

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

134 nodos del catalogo; relaciones de codigo y de plan distinguidas por clase.
