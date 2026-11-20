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
Depende de: CPU x86-64 (plan), Pila inicial CASM (plan).
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

## kernel/syscalls

Recibe operaciones de Ring 3 y comprueba el contrato antes de tocar recursos.

Estado: DISENO. Anillo: 0. Lenguaje: CASM.
Entrada: ABI versionado, registros, capability y buffers declarados.
Salida: Respuesta definida y retorno seguro a Ring 3.
Depende de: Excepciones x86-64 (plan), BEF2 y ABI de BMO-X (plan).
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

## kernel/drivers

Aisla mecanismos de dispositivos del resto del kernel y explicita acceso a puertos/MMIO/DMA.

Estado: DISENO. Anillo: 0. Lenguaje: CASM.
Entrada: Hardware identificado, regiones concedidas e interrupciones comprobadas.
Salida: Operaciones acotadas con estado, tiempo limite y motivo de fallo.
Depende de: Memoria y aislamiento (plan).
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

Prepara imagenes virtuales por run, delega los casos a la sonda QEMU y registra entorno; nunca instala al PC.

Estado: HOST. Anillo: host. Lenguaje: herramienta/evidencia.
Entrada: Paquete Genesis comprobado, puente heredado y QEMU/OVMF.
Salida: Ejecucion o evidencia de la ruta provisional.
Depende de: Puente UEFI provisional (generacion), Genesis: guardian de bytes y tamano (verificacion).
Aceptacion: El perfil actual ring0-abi-probe-0.1 pasa normal, contexto, rechazo ABI y permisos en QEMU; la sonda inicializa banderas de otros perfiles para no contaminar el caso.
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

## kernel/loader

Admite y mapea una imagen SBEF bajo el contrato del proceso.

Estado: DISENO. Anillo: 0. Lenguaje: CASM.
Entrada: Bytes del ejecutable, limites, perfil SBEF y estado de CPU.
Salida: Imagen mapeada con entrada y permisos comprobados o motivo de rechazo.
Depende de: SBEF y congelacion del ABI (plan), Empaquetador ELF64 a SBEF (verificacion), Lector SBEF de referencia (verificacion), SBEF ABI 1 y llamadas desde CPL3 (verificacion), Contrato minimo del cargador SBEF (plan).
Aceptacion: El lector HOST y el prototipo x86-64 ensamblado con LLVM comprueban admision, mapa y rechazo en perfiles fijos. QEMU verifica en CPL3 PTE/marcos/permisos reales, bytes inmutables, rechazo W+X y la region RW mutable; evidencia run-desktop-media-32f9f2682ded.
Pendiente: La sonda LLVM solo reconoce layouts fijos RX, RX/R y RX/R/RW de una a tres regiones; ampliar el cargador CASM a una-ocho regiones, RVA, mapa dinamico, pila y rollback por proceso. La evidencia es QEMU y excluye comparar bytes RW tras ejecutar; falta validar el cargador CASM general.

## kernel/drivers/bus

Descubre xHCI y prueba transporte de comandos con reserva DMA y MMIO supervisora.

Estado: QEMU. Anillo: 0. Lenguaje: CASM.
Entrada: Inventario PCI, entrega UEFI, BAR, RTSOFF/DBOFF y diez paginas LoaderData.
Salida: Respuesta No Op, descriptor de dispositivo y configuracion del primer USB2, parada y revocacion DMA en perfiles separados.
Depende de: Frontera de dispositivos (plan), Espacios y permisos (plan), Prestamo y revocacion DMA (plan).
Aceptacion: QEMU verifica transporte, seleccion de puertos y rechazos. METAL: foto del 16-11 confirma descriptores en AMD puerto 2, CC 01, CS 64 B y MPS 8; Reports/metal-ep0-20261116.json.
Pendiente: Pendientes configuracion de interfaces HID, endpoints interrupt, informes de ambos dispositivos, hotplug asincrono e IOMMU.

## docs/RING0-PLAN.md

Define la evidencia necesaria para congelar SBEF y el ABI.

Estado: DISENO. Anillo: contrato. Lenguaje: contrato.
Entrada: Cargador externo CASM, perfil ISA, fixtures por productor, puentes ABI, runtimes versionados, aislamiento, capacidades, INVOKE y WAIT.
Salida: Contrato congelable con casos de oro, rechazos y medidas.
Depende de: Presupuesto de la entrada Ring 0 (plan), Cargador SBEF (plan).
Aceptacion: QEMU prueba las puertas 1 a 4 de tools/host/profiles.py: carga externa, ISA declarada, fixtures por productor y puentes ABI; varios productores ejecutan el mismo contrato con rechazos comparables.
Pendiente: La puerta 1 sigue parcial. La base x86-64-v1 y el campo ISA SBEF v2 ya estan fijados; falta integrar el chequeo CPUID/XCR0 en el cargador general CASM, cerrar fixtures de algunas parejas productor/enlazador y el ABI entre productores. Los runtimes/imports se agregan despues bajo la puerta 5.

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
Pendiente: Ampliar CASM con CPUID por perfil y cotejarlo con la sonda LLVM kernel/arch/x86_64/cpu/isa_profile_check.inc al cerrar la puerta 1.

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

Coordina la inspeccion, admision, diagnostico y publicacion de ejecutables x86-64; define el futuro flujo adaptadores -> IR BMO -> backend por ISA.

Estado: HOST. Anillo: host. Lenguaje: Python control.
Entrada: ELF64 o PE32+ enlazado para los importadores actuales; fuente/IR de productor mediante adaptadores futuros.
Salida: SBEF admitido, comparacion de builds por archivo y paginas, o rechazo con campo y offset.
Depende de: Empaquetador ELF64 a SBEF (codigo), Perfiles y capas del HOST x86-64 (codigo), Lector SBEF de referencia (codigo), Inspeccion PE32+ x86-64 (codigo).
Aceptacion: profiles publica CapabilityCatalog. El intake MSVC liga la declaracion al hash PE y el SBEF emitido por PowerShell ejecuto el fixture ABI en CPL3 bajo QEMU; evidencia Reports/host-msvc-qemu.json; toolchain no atestado.
Pendiente: Implementar y serializar IR BMO, definir semantica y adaptar productores; la admision de todo compilador no existe. Automatizar procedencia, importar COFF .obj, definir enlace propio, cerrar carga externa SBEF en Ring 3 y anadir imports/runtime solo con semantica propia.

## tools/host/profiles.py

Registra productores, formatos, reglas PE/ELF y destino actual exclusivamente x86-64; declara x86-64-v1 como base y niveles SBEF v2 v1-v4. Enlaza el contrato de diseno IR BMO; backends, paquetes, ABI y NANO-CORE seran especificos por ISA.

Estado: HOST. Anillo: host. Lenguaje: Python.
Entrada: Perfiles de MSVC, LLVM/Clang, GCC y Rust; manifiesto opcional ligado al hash PE.
Salida: Matriz y catalogo de capacidades consultables con `python -B tools/sbef.py profiles`, politica ISA y estado de procedencia.
Depende de: Empaquetador ELF64 a SBEF (codigo), Lector SBEF de referencia (codigo), Inspeccion PE32+ x86-64 (codigo).
Aceptacion: profiles exporta CapabilityCatalog, politica ISA y niveles acumulativos. SBEF v2 escribe el ID ISA en offset 24; v1 heredado implica x86-64-v1; los IDs desconocidos se rechazan.
Pendiente: IR BMO y su serializacion binaria aun no estan implementadas; tampoco la admision de todos los compiladores. La etiqueta SBEF no verifica los opcodes. Falta compilar y validar en QEMU las sondas LLVM, ligar opciones de productor y fixtures a cada nivel, cerrar el chequeo general CASM tras la puerta 1, generar procedencia automaticamente, admitir objetos COFF, certificar clang-cl/lld-link y ejecutar SBEF externo en Ring 3.

## tools/host/importers/elf.py

Convierte segmentos de un ELF64 estatico a regiones SBEF comprobadas.

Estado: HOST. Anillo: host. Lenguaje: Python control.
Entrada: Ejecutable x86-64 freestanding y contrato binario provisional.
Salida: Cabecera, tabla de regiones y bytes de la imagen SBEF.
Depende de: SBEF y congelacion del ABI (codigo), Lector SBEF de referencia (verificacion).
Aceptacion: Admite ELF64 x86-64 estatico dentro del perfil y conserva bytes PT_LOAD; las pruebas de productores se informan por separado.
Pendiente: Probar el mismo paquete externo con el cargador general de Ring 3; los casos Rust, Clang y GCC no acreditan todo su runtime.

## tools/host/sbef/format.py

Valida la imagen SBEF y localiza el campo rechazado.

Estado: HOST. Anillo: host. Lenguaje: Python control.
Entrada: Bytes SBEF y contrato provisional.
Salida: Regiones admitidas o codigo, campo, offset e indice.
Depende de: contrato propio sin dependencias en este catalogo.
Aceptacion: Lee SBEF v1 como x86-64-v1 y v2 con IDs ISA 1-4; rechaza perfil desconocido, version/reservado invalidos, permisos, truncado y solapes.
Pendiente: Compartir vectores ISA, admision y diagnostico con el cargador CASM general; la sonda LLVM aun no lo sustituye.

## tools/host/importers/pe.py

Inspecciona PE32+ independientemente del productor, aplica relocaciones DIR64 internas y admite perfiles SBEF fijos o freestanding limitados.

Estado: QEMU. Anillo: host. Lenguaje: Python control.
Entrada: Ruta de un PE32+ x86-64 pasado al comando de intake de PowerShell.
Salida: Informe con hash, tipo, secciones, directorios, imports, relocaciones y SBEF admitido o rechazo preciso.
Depende de: contrato propio sin dependencias en este catalogo.
Aceptacion: PowerShell inspecciona PE EXE y DLL; una prueba real de MSVC aplica DIR64 y empaqueta cuatro regiones en 388 bytes. El intake con manifiesto emitio SBEF de 792 bytes que ejecuto el ABI en CPL3/QEMU; evidencia Reports/host-msvc-qemu.json; el manifiesto no certifica el compilador.
Pendiente: El cargador QEMU aun no acepta el SBEF RVA generico. Faltan imports e IAT, TLS, load config, unwind, exports, servicios de runtime, procesos externos, intake de objetos COFF y un fixture propio de clang-cl/lld-link.

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
Salida: SBEF desde ELF o PE32+ freestanding, y opciones de inspeccion COFF.
Depende de: HOST: del ejecutable a SBEF (verificacion), Empaquetador ELF64 a SBEF (generacion).
Aceptacion: GCC C, Clang C/C++, Rust y MSVC verifican el ABI en CPL3. MSVC PE produce un paquete de 1887 bytes.
Pendiente: Cargador externo general, revocacion por proceso y perfiles PE que requieran servicios de Windows.

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

Mantiene CLI compatible y delega compilacion de estructura y estilos en Ultra-J/ui/.

Estado: QEMU. Anillo: host. Lenguaje: Python.
Entrada: Vista .ujh, estilos .ujc y atlas de CABINA.
Salida: Vista UJVI con coordenadas logicas independiente del destino.
Depende de: ULTRA-J: bytecode y tema (plan), ULTRA-J: compilador visual (codigo).
Aceptacion: QEMU verifica ambos estados, la accion con Enter, el reinicio con Esc y el rechazo de SBEF W+X.
Pendiente: Conectar eventos por elemento y compositor DIRECTOR; integrar un motor mas amplio si se requiere CSS completo.

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
Salida: SBEF con presentador y vista; ACTION.UJB separado en FAT32.
Depende de: ULTRA-J: estructura y estilos (codigo).
Aceptacion: UJBC v1/v2 interpreta regiones y metodos; QEMU coteja la vista y los 256 bytes de la arena.
Pendiente: Cargar aplicaciones en sesion activa, integrar DIRECTOR y comprobar en metal.

## userspace/services/desktop

Compone superficies y gestiona ventanas y cuatro espacios inspirados en Ultra-LinuX.

Estado: QEMU. Anillo: 3. Lenguaje: Rust.
Entrada: Eventos de entrada, superficies de clientes y capacidad de pantalla.
Salida: Cuadro en RAM, espacio activo, foco, movimiento de ventanas y peticion de cierre desde CABINA.
Depende de: Supervisor Rust de Ring 3 (plan), Mezcla y controles de audio (plan), USB HID de Ring 3 (codigo), Bienvenida del escritorio en Ring 3 (codigo).
Aceptacion: HOST exige presupuesto SBEF y puerta de sesion de hasta 2048 bytes. QEMU registra L1 por CPUID y verifica arranque FAT32, entrada, rechazo de permisos y reuso de cinco marcos.
Pendiente: Entregar marcos al asignador, cargar un SBEF distinto, aislar procesos y conectar el compositor y el planificador.

## userspace/services/desktop/src/keyboard.rs

Convierte eventos de BMO-X en cambios de espacio, foco numerado y movimiento de ventanas.

Estado: HOST. Anillo: 3. Lenguaje: Rust.
Entrada: Scancode normalizado, flanco y modificadores asociados al evento.
Salida: Atajo consumido o evento para el componente enfocado.
Depende de: Escritorio y espacios de trabajo (codigo).
Aceptacion: HOST verifica cambio de espacio, movimiento, repeticion, liberacion y reenvio.
Pendiente: Conectar la capacidad de entrada y probar teclado real en QEMU.

## userspace/services/desktop/src/usb_hid.rs

Traduce informes USB boot en flancos de teclado, movimiento y botones del raton.

Estado: HOST. Anillo: 3. Lenguaje: Rust.
Entrada: Informes de endpoints HID con protocolo boot seleccionado.
Salida: Eventos para atajos, cliente enfocado y puntero.
Depende de: Teclado y atajos del escritorio (codigo).
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
Depende de: Prestamo y revocacion DMA (plan).
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

## contracts/DRIVER-SERVICES.md

Separa protocolos de usuario y concesiones privilegiadas de recursos.

Estado: DISENO. Anillo: contrato. Lenguaje: contrato.
Entrada: Dispositivo, propietario, capacidades, dominio DMA y eventos.
Salida: Condiciones de acceso, espera, fallo y revocacion por servicio.
Depende de: Prestamo y revocacion DMA (plan).
Aceptacion: Un proceso CPL3 recibe solo sus recursos; CPU y DMA rechazan accesos ajenos, incluso tras revocacion.
Pendiente: Implementar procesos, concesiones de MMIO y DMA con IOMMU y eventos de driver.

## userspace/drivers/usb

Descubre interfaces HID boot, decodifica informes y secuencia configuracion/protocolo/endpoints con terminaciones y plazos comprobados.

Estado: QEMU. Anillo: 3. Lenguaje: Rust.
Entrada: Descriptores acotados y reportes recibidos por un transporte autorizado.
Salida: InputService y decoders HID enlazados a sondas y al escritorio RmlUi en perfiles USB QEMU separados; Activation/PendingActivation aun sin transporte de configuracion propio.
Depende de: Contrato de drivers Ring 3 (codigo), Activacion HID con confirmacion (codigo), Eventos xHCI al servicio HID (codigo).
Aceptacion: HOST verifica 18 casos USB y 14 de escritorio. InputService ejecuta en CPL3 QEMU: teclado 260 reportes y raton 4, perfiles separados; CABINA, WAIT, cierre y rechazo SBEF W+X comprobados. Escritorio normal conserva configuracion.
Pendiente: Adaptar el backend vivo a AMD y dos dispositivos simultaneos; conectar activacion de usuario al transporte autorizado; hotplug, parada y recuperacion del escritorio nativo pendientes.

## Ultra-J/driver.py

Valida registros declarativos de driver y solicita recursos sin concederlos.

Estado: HOST. Anillo: host. Lenguaje: Python.
Entrada: main.uj, dependencias locales y backends SBEF ABI 1 x86-64.
Salida: Registro HOST con hashes, orden y recursos; RuntimeReady falso y sin capacidades concedidas.
Depende de: Contrato de drivers Ring 3 (codigo), Lector SBEF de referencia (verificacion).
Aceptacion: HOST rechaza ciclos, escapes, privilegios desconocidos y SBEF o presupuestos invalidos; CLI conserva los crates existentes.
Pendiente: Integrar registro con concesiones del NANO-CORE, proceso SBEF aislado y transporte de dispositivo.

## Reports

Expone fase USB, motivo, siguiente paso y pulsos de Ring 0 sin necesitar entrada; exporta evidencia en HOST.

Estado: QEMU. Anillo: host. Lenguaje: Python.
Entrada: Capacidad de diagnostico, resultados QEMU y BOOTLOG previo a ExitBootServices.
Salida: Panel automatico y latest.txt/json con fuentes separadas.
Depende de: Buses, recursos y DMA (codigo), Escritorio y espacios de trabajo (codigo).
Aceptacion: QEMU verifica puerto 2 a alta/completa velocidad, contextos EP0 y rechazo de puertos vacio/fuera de rango sin fallback. REPORTES SBEF 11461 B, RX 8073 B; sonda dirigida 4091 B.
Pendiente: METAL confirma descriptores del puerto 2; faltan entrada HID, historial general, excepciones fatales y persistencia FAT32 del runtime.

## Ultra-J/ui/style.py

Valida el perfil UJC acotado y sus propiedades soportadas.

Estado: HOST. Anillo: host. Lenguaje: Python.
Entrada: Hojas .ujc en HOST.
Salida: Reglas validadas o error preciso.
Depende de: contrato propio sin dependencias en este catalogo.
Aceptacion: Reorganizacion conserva UJVI byte por byte. Banco ULTRA-J: 26 pruebas, una omitida, sin fallos; evidence/ui-layers-host.json.
Pendiente: CSS completo y un motor de layout general no estan implementados.

## Ultra-J/ui/view.py

Transforma .ujh y reglas en geometria validada y listas UJVI.

Estado: HOST. Anillo: host. Lenguaje: Python.
Entrada: Estructura, reglas, atlas y limites de vista.
Salida: Listas binarias para el presentador Ring 3.
Depende de: ULTRA-J: perfil de estilos (codigo), ULTRA-J: bytecode y tema (generacion).
Aceptacion: Reorganizacion conserva UJVI byte por byte. Banco ULTRA-J: 26 pruebas, una omitida, sin fallos; evidence/ui-layers-host.json.
Pendiente: CSS completo y un motor de layout general no estan implementados.

## tools/desktop/rmlui

Construye RmlUi/FreeType en HOST y empaqueta recursos, UJBC y DLL; prueba el motor C++ con dibujador Rust.

Estado: HOST. Anillo: host. Lenguaje: C++ / Python.
Entrada: RML, RCSS, main.uj y dependencias fijadas por commit.
Salida: Paquete HOST con hashes, dos imagenes y mediciones del proceso; no SBEF.
Depende de: ULTRA-J: compilador inicial (codigo), ULTRA-J: verificador y reciclador (codigo), Dibujo CPU Rust para RmlUi (codigo), Sesion del motor C++ RmlUi (codigo).
Aceptacion: Sesion en memoria y animacion real pasan live.py; la DLL conserva rechazo SBEF y el objeto del adaptador no importa Kernel32 directamente.
Pendiente: Motor C++ freestanding, asignador y servicios propios, eventos DIRECTOR/ULTRA-J nativos y perfil de carga medido; DLL Windows rechazada.

## userspace/services/desktop/src/rmlui.rs

Dibuja triangulos con RGBA o Alpha8 blanco premultiplicado sobre buffers prestados, sin heap ni llamadas de SO.

Estado: QEMU. Anillo: 3. Lenguaje: Rust.
Entrada: Vertices, textura acotada, superficie XRGB y rectangulo de recorte.
Salida: Pixeles propios de la superficie; rechazo antes de escribir ante dimensiones o vertices invalidos.
Depende de: contrato propio sin dependencias en este catalogo.
Aceptacion: 256 coberturas Alpha8 iguales a RGBA; sonda CPL3 con ambos formatos y pixeles iguales a HOST; rechazo W+X conservado.
Pendiente: Invalidacion avanzada y sesiones prolongadas; el motor completo ya dibuja en el candidato DIRECTOR de un panel.

## tools/desktop/rmlui/guest.ps1

Construye el mismo dibujador como SBEF freestanding y compara pixeles reales de QEMU con HOST.

Estado: QEMU. Anillo: host. Lenguaje: PowerShell / Rust / Python.
Entrada: Run ABI CASM verificado y codigo Rust compartido.
Salida: SBEF de 7421 bytes, captura y reporte QEMU de CPL3 con RGBA y Alpha8; no instala escritorio ni motor completo.
Depende de: Dibujo CPU Rust para RmlUi (codigo), SBEF ABI 1 y llamadas desde CPL3 (verificacion).
Aceptacion: 256 pixeles logicos y 65536 fisicos iguales a HOST; dos casos pasan incluido W+X; ninguna guarda ampliada.
Pendiente: Pruebas del motor completo, eventos, cierre de recursos, sesion permanente y METAL.

## userspace/services/desktop/src/welcome.rs

Muestra tres fases visuales despues de admision y permisos, entre el gato CASM y el escritorio ULTRA-J.

Estado: QEMU. Anillo: 3. Lenguaje: Rust.
Entrada: Capacidades de pantalla, entrada y reloj; perfil optativo -Welcome.
Salida: Bienvenida breve con WAIT; primera entrada preservada para el escritorio.
Depende de: BEF2 y ABI de BMO-X (codigo).
Aceptacion: QEMU compara dos cuadros del gato, tres fases con llamador CPL3, llegada al escritorio y salto F2 que abre CABINA; rechazo W+X sigue pasando.
Pendiente: Presentacion RmlUi completa y validacion en METAL; este perfil no certifica dispositivos USB.

## tools/desktop/rmlui/memory_files.h

Sustituye acceso a archivos del adaptador por una tabla de recursos inmutables con cursores acotados.

Estado: QEMU. Anillo: host. Lenguaje: C++.
Entrada: Hasta ocho recursos con nombre plano, bytes prestados y longitud.
Salida: Lectura y busqueda acotadas; rechazo de rutas y recursos ausentes.
Depende de: contrato propio sin dependencias en este catalogo.
Aceptacion: La sesion real lee RML/RCSS/fuentes desde memoria; ruta .. y recurso ausente se rechazan sin abrir disco desde el adaptador.
Pendiente: Productor de recursos desde paquetes del escritorio; el visor nativo actual usa cuatro recursos incrustados y validados.

## tools/desktop/rmlui/engine.cpp

Expone reloj, recursos, eventos, destino prestado y omision optativa de cuadros preservados sin cambios, mediante ABI C de aplicacion.

Estado: HOST. Anillo: host. Lenguaje: C++.
Entrada: Tabla de recursos, tiempo inyectado, entrada y callback de accion ULTRA-J.
Salida: Cuadros Rust CPU, plazo de actualizacion y diagnosticos de ciclo de vida y perfil visual.
Depende de: Recursos de interfaz en memoria (codigo), Dibujo CPU Rust para RmlUi (codigo), Motor RmlUi compilado para x86-64 (codigo).
Aceptacion: Animaciones RCSS de opacidad/ancho/color verificadas; puntero y Enter; reentrada bloqueada; cierre limpio; objeto sin llamadas Kernel32 directas.
Pendiente: Conectar la API de sesion y el reloj al escritorio DIRECTOR; guest.cpp ya verifica un arranque nativo independiente sin excepciones.

## tools/desktop/rmlui/live.py

HOST entrega recursos al motor real, avanza tiempo determinista y verifica pixeles, entrada, acciones y rechazos.

Estado: HOST. Anillo: host. Lenguaje: Python.
Entrada: Paquete HOST de RmlUi y UJBC del ejemplo.
Salida: PNG, GIF de cuadros reales e informe HOST con pruebas, recursos y costes.
Depende de: Sesion del motor C++ RmlUi (verificacion), ULTRA-J: compilador inicial (codigo), ULTRA-J: verificador y reciclador (codigo).
Aceptacion: Movimiento reducido estable, transiciones interpoladas, accion aceptada/rechazada, repeticion Enter, reinicializacion y ausencia de actualizaciones pendientes al terminar.
Pendiente: Planificacion y animacion del escritorio nativo permanente; el motor reducido ya pasa rmlui-native-validation en CPL3.

## tools/desktop/rmlui/memory.py

Mide atlas compactos sin perdida, igualdad visual y trabajo evitado en reposo con reactivacion por entrada.

Estado: HOST. Anillo: host. Lenguaje: Python / C++ / Rust.
Entrada: Sesion real RmlUi, recursos fijados y referencia visual opcional.
Salida: Informe HOST con bytes retenidos, cuadros omitidos, tiempos y coste acotado; no RAM total del sistema.
Depende de: Sesion del motor C++ RmlUi (verificacion), Sonda SBEF del dibujador comun (verificacion).
Aceptacion: 15 atlas bajan de 1277952 a 319488 bytes; tres imagenes iguales; 30 cuadros quietos sin triangulos; entrada y animacion redibujan; destino nuevo se refresca.
Pendiente: Medir sesiones prolongadas y politica de reposo permanente. El visor nativo ya limita heap a 4 MiB y comprueba igualdad visual con atlas 256.

## tools/desktop/rmlui/native/build.py

Compila Core real RmlUi, FreeType y libc++/libc++abi como bibliotecas ELF64 sin sustituirlas por una DLL Windows.

Estado: HOST. Anillo: host. Lenguaje: Python / CMake / C++.
Entrada: Fuentes oficiales fijadas, Clang ELF, NMake y tipos C de musl sin numeros de syscall Linux.
Salida: 282 objetos ELF64 y bibliotecas estaticas; no ejecutable ni SBEF.
Depende de: Dependencias reales del motor nativo (codigo).
Aceptacion: Build completo de Core, fuentes intactas validadas por SHA256/revision y un include de streams omitido explicitamente en copia de build.
Pendiente: Se conserva como etapa de bibliotecas; ejecutable y runtime nativos se comprueban en rmlui-native-application.

## tools/desktop/rmlui/native/audit.py

Valida archivos ELF de destino, enlaza de verdad las bibliotecas y expone servicios pendientes sin aceptar un relocatable como programa.

Estado: HOST. Anillo: host. Lenguaje: Python / LLVM.
Entrada: RmlUi Core, FreeType y libc++ con libc++abi incorporada, compilados para x86-64.
Salida: native-results.json, unresolved.txt y evidencia de rechazo SBEF del ET_REL.
Depende de: contrato propio sin dependencias en este catalogo.
Aceptacion: 282 miembros ELF64 maquina 62; 70 simbolos pendientes inventariados; rechazo ELF-HEADER/e_type; tests rechazan COFF, otra CPU y archivos alterados.
Pendiente: Inventario de bibliotecas aisladas; el ejecutable nuevo resuelve sus servicios C. Conservar las comprobaciones al ampliar el perfil.

## tools/desktop/rmlui/native/services.c

Payload Ring 3 compilado y admitido por HOST: une calculo musl sin servicios Linux, heap de 4 MiB y familia new/delete al perfil nativo de un cliente.

Estado: QEMU. Anillo: 3. Lenguaje: C / C++.
Entrada: Solicitudes de memoria, formato/numeros y recursos del Core RmlUi/FreeType.
Salida: Asignaciones con propiedad y alineacion, log de fallos y denegacion explicita de disco/entorno.
Depende de: contrato propio sin dependencias en este catalogo.
Aceptacion: ELF sin simbolos pendientes; pruebas de alineacion, calloc, overflow, realloc fallido y disco denegado; pico de heap 3028176 bytes.
Pendiente: Recuperacion de proceso y medicion prolongada; no runtime POSIX general ni seguridad DMA/USB probada por esta interfaz.

## tools/desktop/rmlui/native/guest.cpp

Payload de escritorio Ring 3 construido por HOST desde C++/Rust/ULTRA-J: carga RML/RCSS/fuentes, dibuja en CPU y ejecuta UJBC con recursos acotados.

Estado: QEMU. Anillo: 3. Lenguaje: C++ / Rust / ULTRA-J.
Entrada: SBEF del perfil rmlui-native-v1, cuatro recursos inmutables y eventos PS2/Enter.
Salida: Visor independiente o candidato DIRECTOR de un panel; superficie XRGB 1280x800, acciones UJBC nativas y presentacion GOP entera.
Depende de: Motor RmlUi compilado para x86-64 (codigo), Runtime acotado de la interfaz nativa (codigo), Dibujo CPU Rust para RmlUi (codigo), ULTRA-J: compilador inicial (codigo), Politica Rust del escritorio nativo (codigo), Informes USB al escritorio nativo (codigo).
Aceptacion: CPL3, Enter/clic y pixeles iguales a HOST; candidato FAT32 prueba espacios, Super+Q y reapertura sin terminar la base. Evidencia Ultra-J/evidence/rmlui-desktop-fat32.json.
Pendiente: Migrar CABINA/DOOM y multiples aplicaciones; reloj/animacion, descarga de procesos y USB HID en METAL.

## tools/boot/rmlui_native_capture.py

Observa estados, memoria, framebuffer, acciones y cierre del motor real sin simular servicios del invitado.

Estado: QEMU. Anillo: host. Lenguaje: Python / QMP.
Entrada: QEMU con SBEF nativo, perfil de sesion explicito y simbolos verificados.
Salida: Informe QEMU, capturas y comparacion HOST de todos los pixeles; rechazo W+X y huella para visor.
Depende de: Interfaz RmlUi y ULTRA-J nativa (codigo), Dependencias reales del motor nativo (codigo).
Aceptacion: SBEF y pixeles nativos comprobados, rechazo W+X antes de copia; perfiles USB separados prueban entrada sin su alternativa PS2 y comprueban reserva DMA/mapeos supervisores.
Pendiente: Pruebas prolongadas, fallos recuperables y motor permanente en hardware fisico.

## userspace/services/desktop/src/native_policy.rs

Adapta DIRECTOR existente a foco, cuatro espacios y nueve posiciones de ventana sin compartir el framebuffer mutable.

Estado: QEMU. Anillo: 3. Lenguaje: Rust.
Entrada: Scancodes Set1 y eventos de apertura.
Salida: Identidad, foco y espacio de los paneles ULTRA-J y MSVC en el escritorio; Super+Espacio abre ULTRA-J y F3 abre MSVC en el perfil opcional.
Depende de: contrato propio sin dependencias en este catalogo.
Aceptacion: QEMU comprueba foco, cambio de espacio, Super+Q y bloqueos desde el teclado USB, y verifica los pixeles del panel compilado con MSVC.
Pendiente: Aplicaciones en procesos separados, descarga de recursos por proceso, distribucion de teclado y verificacion USB fisica.

## tools/desktop/rmlui/native/media.py

Construye el perfil de escritorio FAT32 y las variantes xHCI de teclado/raton para QEMU, sin sustituir el candidato fisico.

Estado: QEMU. Anillo: host. Lenguaje: Python / LLVM / CASM / C++ / Rust.
Entrada: Runs ABI y gato CASM verificados, ELF/SBEF nativo con hashes y selector explicito de perfil USB.
Salida: EFI e INICIO con SBEF desde FAT32; perfiles QEMU con reserva DMA supervisada, etapa xHCI y reportes.
Depende de: Interfaz RmlUi y ULTRA-J nativa (codigo), Inspeccion acotada de FAT32 (codigo), Buses, recursos y DMA (codigo), Informes USB al escritorio nativo (codigo), Presentacion GOP por CPU (codigo), GPU / NVIDIA / Inventario PCI (codigo), AMD-Vi / Inventario UEFI (codigo), AMD-Vi / Captura Ring 0 (codigo), PCI / Inventario de solicitantes DMA (codigo), Almacenamiento / Estado posterior a UEFI (codigo), GOP / Escritorio nativo 1920x1080 (codigo), GPU / NVIDIA / Lectura MMIO (codigo).
Aceptacion: FAT32: GOP 1280x800 y 1024x768, W+X rechazado, BOOTLOG/SBEF releidos. USB: teclado y raton en perfiles separados, W+X rechazado, limites de imagen comprobados y deploy.ps1 rechaza perfiles solo-QEMU.
Pendiente: Arranque fisico del candidato y backend USB AMD completo; la supervision DMA no acredita IOMMU ni aislamiento de dispositivos hostiles.

## tools/boot/fat32_read.py

Lee la primera particion GPT/FAT32 de imagenes de prueba sin modificarlas.

Estado: HOST. Anillo: host. Lenguaje: Python.
Entrada: Imagen con sectores de 512 bytes, dos FAT y rutas 8.3.
Salida: Bytes del archivo con geometria, limites, espejos y cadenas comprobados.
Depende de: contrato propio sin dependencias en este catalogo.
Aceptacion: Cuatro tests de cadenas fragmentadas, limites, ciclos y discrepancias entre FAT.
Pendiente: No es reparador de discos ni controlador de almacenamiento del invitado.

## tools/desktop/rmlui/native/deploy.ps1

Copia exclusivamente el candidato QEMU aprobado al volumen FAT32 A: y verifica hashes.

Estado: HOST. Anillo: host. Lenguaje: PowerShell.
Entrada: Manifiesto aprobado y volumen existente; no formatea ni cambia NVRAM.
Salida: EFI/BMO-X2/DESKTOP.EFI y BMO-X2/DESKTOP con recibo DEPLOY.JSON.
Depende de: Builder UEFI y perfiles xHCI del escritorio (codigo).
Aceptacion: METAL: propietario confirma UI nativa en GOP 1920x1080 con foto y BOOTLOG; Reports/rmlui-desktop-metal-20261116.json. Variante silenciosa nueva: QEMU 2/2 y copia A: verificada.
Pendiente: Confirmar variante silenciosa en METAL. USB HID aun sin conectar al candidato nativo.

## tools/desktop/rmlui/native/register-desktop.ps1

Registra el escritorio o el ensayo de inventario PCI NVIDIA como entradas UEFI independientes.

Estado: HOST. Anillo: host. Lenguaje: PowerShell.
Entrada: Volumen A: FAT32, recibo DEPLOY.JSON, hashes de los tres archivos activos y evidencia QEMU para el ensayo NVIDIA.
Salida: BMO-X2 Desktop (RmlUi) apunta a DESKTOP.EFI. BMO-X2 (con NVIDIA) apunta a NVIDIA.EFI.
Depende de: Candidato separado en FAT32 fisico (codigo).
Aceptacion: Registro HOST verifica el dispositivo, la ruta y la presencia de la entrada. Al crearla, verifica que se agregue al final del orden anterior.
Pendiente: METAL confirmo la entrada NVIDIA y MMIO del GA106. La siguiente prueba de arranque requiere un candidato con DMA nativo.

## userspace/drivers/usb/src/activation.rs

Secuencia configuracion, protocolo por interfaz y endpoints; no supone exito al emitir una peticion.

Estado: HOST. Anillo: 3. Lenguaje: Rust.
Entrada: Descriptores validados, velocidad USB2, slot y generacion del propietario, reloj monotono y terminaciones cotejadas por transporte.
Salida: Peticiones acotadas y estado Ready solo tras todas las confirmaciones; fallos y expiracion bloquean sin reciclar DMA.
Depende de: Contexto interrupt IN USB2 (codigo).
Aceptacion: 22 tests USB HOST; rechazo de propietario/secuencia/fase obsoletos, STALL, residual, expiracion y plazos invalidos. Build no_std x86_64.
Pendiente: Conexion real al transporte xHCI del escritorio; sin evidencia de USB HID en METAL.

## userspace/drivers/usb/src/xhci.rs

Calcula DCI e intervalo de cada endpoint descubierto, sin asumir endpoint 0x81.

Estado: HOST. Anillo: 3. Lenguaje: Rust.
Entrada: Interfaz HID boot y velocidad low/full/high; perfil de hasta 64 bytes.
Salida: Campos xHCI con puntero dequeue cero, que solo el transporte autorizado puede completar.
Depende de: contrato propio sin dependencias en este catalogo.
Aceptacion: Pruebas de endpoint 15, mascara de contexto, intervalos FS/LS 1..255 y HS 1..16; rechazo de direccion, tamano e intervalo invalidos.
Pendiente: Envio mediante transporte de propietario con anillo DMA reservado y terminacion de Configure Endpoint.

## userspace/drivers/usb/src/completion.rs

Coteja eventos copiados antes de avanzar Activation o publicar un informe en InputService.

Estado: HOST. Anillo: 3. Lenguaje: Rust.
Entrada: Evento coherente, ciclo consumidor, TRB esperado, slot, endpoint y fuente local vigente.
Salida: Activacion confirmada o informe unico; conserva el ticket ante presion de cola y deja eventos ajenos a su propietario.
Depende de: Activacion HID con confirmacion (codigo).
Aceptacion: 27 tests HOST y build no_std: ciclo, pointer, slot, endpoint, tipo, ED, activacion previa, doble entrega y fuente retirada.
Pendiente: Lector del anillo real, ERDP, envio de comandos y DMA autorizado del escritorio nativo; sin USB fisico acreditado.

## tools/desktop/rmlui/native/retire-legacy.ps1

Archiva con hash y retira exactamente los cuatro archivos del BMO-X2 anterior desregistrado.

Estado: HOST. Anillo: host. Lenguaje: PowerShell.
Entrada: Entrada nueva presente, manifiesto activo y cuatro rutas antiguas exactas.
Salida: Solo perfil nuevo en BMO-X2; archivo historico dentro del proyecto; Linux/ULTRA y otros EFI fuera de la lista.
Depende de: Candidato separado en FAT32 fisico (codigo).
Aceptacion: Cuatro archivos archivados y retirados; tres archivos activos conservan hash. Reports/fat32-retired-legacy.json.
Pendiente: No es limpieza general de discos ni de builds; no cambia firmware ni particiones.

## tools/desktop/rmlui/native/usb_input.rs

Payload Ring 3 compilado y admitido por HOST: recibe informes escalares mediados y entrega cambios de teclado o raton a RmlUi/DIRECTOR mediante InputService.

Estado: QEMU. Anillo: 3. Lenguaje: Rust / ABI C.
Entrada: Teclado boot y descriptor HID del raton en modo Report, con longitud por transferencia xHCI.
Salida: Scancodes, ejes y rueda relativos, y transiciones de los tres botones aun con ID HID separados. Ring 3 recorta al escritorio y calcula el byte de LED del teclado.
Depende de: USB HID de Ring 3 (codigo), xHCI USB2 con dos dispositivos (codigo).
Aceptacion: CPL3: Enter, espacios, Super+Q/reapertura via USB teclado; movimiento, resaltado sin raster, clic primario, transiciones derecha/central y rueda via USB raton.
Pendiente: Confirmar el descriptor y comportamiento del raton fisico. Los campos usados deben estar dentro de los primeros ocho bytes.

## kernel/drivers/bus/native/controller.inc

Sonda ASM transitoria de Ring 0: descubre bancos MMIO, configura dos slots y entrega informes HID mediados al escritorio; no reemplaza la implementacion estable CASM.

Estado: QEMU. Anillo: 0. Lenguaje: ASM x86-64.
Entrada: Controlador xHCI admitido, dos puertos directos USB2 y reserva UEFI supervisora.
Salida: Informes escalares para Ring 3, puntero visible desde el primer cuadro y diagnostico de identidad, transferencia o puerto.
Depende de: contrato propio sin dependencias en este catalogo.
Aceptacion: QEMU verifica teclado y raton simultaneos, rechazo W+X, puertos vacios y parada con revocacion PCI/MMIO.
Pendiente: Prueba AMD del 17-11: USB ON, fase 199, CC 13 y puntero en movimiento con latencia. Falta medir respuesta fisica del puntero tras reducir el redibujado.

## kernel/drivers/display/GOP/gop_stage.inc

Sonda ASM transitoria de Ring 0: el puente prepara el modulo CPU/GOP separado de xHCI. INVOKE 9 copia un cuadro e INVOKE 10 presenta regiones en escala 1.

Estado: QEMU. Anillo: 0. Lenguaje: ASM x86-64.
Entrada: Superficie XRGB validada de 1280x800, punto de origen y geometria GOP.
Salida: Cuadro escalado, hasta 204 pixeles por caja de cursor o 102400 por franja de estado.
Depende de: contrato propio sin dependencias en este catalogo.
Aceptacion: QEMU comprueba restauracion del cursor y que los bloqueos actualizan la franja sin cuadro completo.
Pendiente: Medir latencia fisica y especializar la copia en otras escalas GOP. Las demas escalas usan la presentacion completa.

## kernel/drivers/display/GOP/full_hd.inc

Publica en GOP cada pixel producido por RmlUi y el raster de Ring 3 a 1920x1080.

Estado: QEMU. Anillo: 0. Lenguaje: ASM x86-64.
Entrada: Modo GOP exacto 1920x1080, superficie XRGB y regiones de puntero o franja de estado.
Salida: Cuadro de 2073600 pixeles y regiones directas de puntero y bloqueos, con retorno al presentador base en otros modos.
Depende de: contrato propio sin dependencias en este catalogo.
Aceptacion: QEMU coteja la superficie nativa con GOP, detecta detalle ausente en el escalado anterior y verifica cursor y modo base.
Pendiente: Nitidez confirmada por el propietario en METAL. El presentador NVIDIA acelerado requiere un backend propio.

## kernel/drivers/GPU/NVIDIA/pci_probe.inc

Sonda ASM transitoria del puente UEFI antes de ExitBootServices. Lee PCI del segmento 0 y conserva CPU/GOP como presentador.

Estado: QEMU. Anillo: 0. Lenguaje: ASM x86-64.
Entrada: Inventario PCI de clase grafica, seleccionado con --nvidia-probe.
Salida: GPULOG.TXT con recuentos, identidad NVIDIA, PCI Command y los seis registros BAR de la funcion grafica inventariada.
Depende de: contrato propio sin dependencias en este catalogo.
Aceptacion: QEMU coteja BDF y BAR de su VGA con QMP y verifica escritorio y rechazo SBEF W+X. METAL confirmo RTX 3060 10DE:2504, sus bases BAR y GOP a 1920x1080.
Pendiente: La sonda MMIO confirmada en METAL usa este inventario como entrada. Falta la prueba GSP.

## kernel/drivers/GPU/NVIDIA/mmio_probe.inc

Sonda transitoria UEFI: confirma limites de BAR0 y lee la identidad interna exclusivamente en la RTX 3060 10DE:2504.

Estado: QEMU. Anillo: 0. Lenguaje: ASM x86-64.
Entrada: BDF y BAR0 del inventario, protocolo EFI PCI I/O, identidad PCI y Command con memoria habilitada y bus mastering apagado.
Salida: Longitud BAR0, palabra PMC_BOOT_0 y estado del ensayo en GPULOG.TXT.
Depende de: GPU / NVIDIA / Inventario PCI (codigo).
Aceptacion: QEMU coteja la longitud BAR0 de VGA con QMP y omite la lectura NVIDIA. METAL confirmo BAR0 de 16 MiB y NV_PMC_BOOT_0 B76000A1 (GA106 A1).
Pendiente: Acreditar inicio de GSP y una operacion GPU verificable antes de transferir la salida de pantalla.

## tools/host/gpu/firmware.py

Comprueba el conjunto original de una release GSP, por longitud y huella de referencia.

Estado: HOST. Anillo: host. Lenguaje: Python.
Entrada: Cuatro binarios locales NVIDIA de la release solicitada y manifiesto de huellas.
Salida: Informe HOST de identidad, archivos y huellas. El layout nativo identifica imagen, version y firma GA10x dentro del ELF64 RISC-V.
Depende de: GPU / NVIDIA / Lectura MMIO (plan).
Aceptacion: Cuatro archivos verificados para 570.144 y 615.78.08. El layout 615.78.08 coteja la version interna y rechaza cabecera truncada, version distinta y secciones solapadas.
Pendiente: Construir los metadatos y colas DMA, y verificar respuesta del GSP nativo con 615.78.08.

## tools/host/gpu/radix3.py

Codifica las paginas del directorio Radix3 que enumera la imagen de firmware mediante IOVA.

Estado: HOST. Anillo: host. Lenguaje: Python.
Entrada: IOVA asignadas para las paginas del directorio y las paginas ordenadas de firmware.
Salida: IOVA raiz y 15 paginas de directorio para la imagen GA10x 615.78.08.
Depende de: HOST / Firmware NVIDIA GA10x (verificacion).
Aceptacion: Un recorrido independiente reconstruye las 6590 paginas de la imagen con IOVA no contiguas y coteja SHA-256. Rechaza cinco entradas invalidas.
Pendiente: Vincular las IOVA al dominio de la RTX, construir metadatos y colas y confirmar el arranque en hardware.

## tools/host/gpu/ivrs.py

Lee la descripcion ACPI IVRS y coteja las funciones PCI indicadas con los rangos IVHD.

Estado: HOST. Anillo: host. Lenguaje: Python.
Entrada: IVRS del firmware mediante Windows o archivo, y los BDF solicitados.
Salida: Unidad AMD-Vi, base, segmento, alcance y alias descritos por el firmware.
Depende de: Buses, recursos y DMA (verificacion).
Aceptacion: HOST verifico que la RTX y su audio aparecen en la unidad AMD-Vi 00:00.2 del equipo.
Pendiente: Entregar los solicitantes de IVRS al dominio nativo y verificar la concesion y revocacion de DMA.

## tools/host/gpu/qemu_dma.py

Comprueba traduccion, bloqueo e invalidacion DMA en AMD-Vi de QEMU con EDU mediante qtest.

Estado: QEMU. Anillo: host. Lenguaje: Python.
Entrada: q35, AMD-Vi, EDU y paginas virtuales de datos, eventos y comandos.
Salida: Evidencia de transferencia, fallos DMA, invalidacion completada y bus mastering cerrado.
Depende de: Buses, recursos y DMA (verificacion).
Aceptacion: QEMU transfiere 14 bytes al destino traducido y conserva RAM fuera de rango y tras revocar.
Pendiente: La sonda CPL0 ya repite el ensayo con EDU. Falta llevar el dominio a AMD-Vi fisico.

## kernel/drivers/bus/amdvi/edu_probe.S

Sonda ASM transitoria despues de ExitBootServices. Programa AMD-Vi en QEMU y prueba DMA de EDU.

Estado: QEMU. Anillo: 0. Lenguaje: ASM x86-64.
Entrada: Traspaso UEFI, nueve paginas EfiLoaderData, QEMU TCG q35, dispositivo EDU y AMD-Vi.
Salida: Informe serial de concesion, rechazo, revocacion y cierre, cotejado por HOST.
Depende de: Buses, recursos y DMA (verificacion).
Aceptacion: QEMU coteja control y bases de AMD-Vi despues de ExitBootServices. Verifica transferencia de ocho bytes, bloqueo por rango y revocacion. Rechaza ausencia de AMD-Vi y omision de invalidacion.
Pendiente: Verificar dominio y retencion de paginas en AMD-Vi de METAL.

## kernel/drivers/bus/amdvi/firmware_probe.S

Sonda ASM transitoria antes de ExitBootServices. Valida IVRS y la base PCI y lee cinco registros AMD-Vi mediante CPU I/O 2.

Estado: QEMU. Anillo: 0. Lenguaje: ASM x86-64.
Entrada: Tabla de sistema UEFI, RSDP, XSDT y una sola unidad IVHD del segmento PCI 0.
Salida: GPULOG.TXT con IVRS, BDF, base PCI, control, tabla, colas y estado AMD-Vi.
Depende de: HOST / Inventario AMD-Vi (verificacion).
Aceptacion: QEMU q35 coteja base PCI y registros con QMP y distingue IVRS ausente. METAL confirmo unidad 00:00.2, decode activo y cinco registros, con traduccion y colas desactivadas antes de ExitBootServices.
Pendiente: Usar el inventario para preparar el dominio de la RTX.

## kernel/drivers/bus/amdvi/post_ebs_probe.inc

Lee los cinco registros AMD-Vi despues de ExitBootServices. Abre y revoca dos paginas MMIO de solo lectura antes de iniciar USB.

Estado: QEMU. Anillo: 0. Lenguaje: ASM x86-64.
Entrada: Captura UEFI valida, capacidad PCI cotejada, mapa final UEFI y tablas propias CASM del escritorio nativo.
Salida: Captura fija en contexto supervisor. INVOKE entrega seis escalares al pie del escritorio y a la serie de QEMU.
Depende de: AMD-Vi / Inventario UEFI (codigo).
Aceptacion: QEMU coteja registros y permisos de las dos paginas y arranca sin AMD-Vi. METAL cotejo los cinco registros en GPULOG y el escritorio Ring 0; la traduccion siguio desactivada.
Pendiente: Acreditar dominio DMA con continuidad de USB y almacenamiento antes de arrancar GSP.

## tools/boot/amdvi_xhci.py

Usa qtest para configurar dominios distintos para EDU y xHCI en el escritorio virtual.

Estado: QEMU. Anillo: host. Lenguaje: Python.
Entrada: QEMU q35, AMD-Vi, EDU, USB dual activo y reservas UEFI del invitado.
Salida: Transferencia traducida, rechazos DMA y contadores HID antes y despues de revocar EDU.
Depende de: AMD-Vi / Traduccion y revocacion virtual (codigo), xHCI USB2 con dos dispositivos (verificacion), AMD-Vi / Dominios en el invitado (verificacion).
Aceptacion: QEMU verifico 8 B en la pagina concedida, rechazo fuera de rango y tras invalidar, y 2 informes de teclado y 1 de raton en cada etapa.
Pendiente: Poner bajo control nativo la lista de solicitantes activos y probar el almacenamiento durante el siguiente ensayo.

## kernel/drivers/bus/amdvi/coexist_guest.inc

Sonda exclusiva de QEMU TCG. Ring 0 comprueba bus masters y configura, invalida y cierra dos dominios AMD-Vi.

Estado: QEMU. Anillo: 0. Lenguaje: ASM x86-64.
Entrada: Escritorio USB dual activo, EDU, reservas UEFI propias y orden fija del banco QEMU. El perfil PCIe descubre el BDF alto y reserva una tabla de 96 paginas.
Salida: Estado de rechazo, tablas y colas propios y comprobantes de invalidacion y cierre.
Depende de: AMD-Vi / Captura Ring 0 (codigo).
Aceptacion: QEMU coteja DTE, invalidacion y DMA en un bus alto. Conserva HID y SATA y comprueba que un segundo EDU con BME no accede sin un dominio concedido.
Pendiente: Integrar la transicion con los solicitantes fisicos, validar sus reservas y probar almacenamiento real antes de activar el dominio para NVIDIA.

## kernel/drivers/bus/amdvi/dma_census.inc

Captura los BDF del segmento PCI 0 con bus mastering habilitado despues de arrancar xHCI.

Estado: QEMU. Anillo: 0. Lenguaje: ASM x86-64.
Entrada: Configuracion PCI del segmento 0 y BDF del xHCI activo en el contexto supervisor.
Salida: Total y hasta 64 registros leidos por INVOKE. F2 muestra el inventario en RmlUi.
Depende de: AMD-Vi / Captura Ring 0 (codigo), xHCI USB2 con dos dispositivos (codigo).
Aceptacion: QEMU coteja PCI con qtest, incluido un xHCI detras de un puente, con y sin AMD-Vi. En METAL F2 mostro los 15 BDF y el xHCI 2b:00.3. HOST cotejo su cobertura IVRS.
Pendiente: Validar la transicion DMA con USB y almacenamiento fisicos.

## kernel/drivers/storage/handoff_uefi.inc

Registra los recursos MMIO de hasta dos controladores AHCI o NVMe del segmento PCI 0 mediante EFI PCI I/O.

Estado: QEMU. Anillo: 0. Lenguaje: ASM x86-64.
Entrada: Dispositivos y BAR asignados por UEFI.
Salida: Recuento, BDF, identidad, clase, PCI Command y limite del BAR en contexto supervisor.
Depende de: contrato propio sin dependencias en este catalogo.
Aceptacion: QEMU coteja BAR, clase y tamano con QMP para AHCI y NVMe.
Pendiente: Cotejar esos recursos en el equipo fisico.

## kernel/drivers/storage/handoff_post.inc

Coteja el BAR con PCI y el mapa final. Lee el estado de AHCI y NVMe y revoca la ventana temporal antes de xHCI.

Estado: QEMU. Anillo: 0. Lenguaje: ASM x86-64.
Entrada: Recursos validados por UEFI, contexto supervisor y copia final del mapa de memoria.
Salida: Estado de motores y comandos AHCI, CC y CSTS de NVMe. F3 publica la captura en RmlUi.
Depende de: Almacenamiento / Recursos UEFI AHCI y NVMe (codigo), PCI / Inventario de solicitantes DMA (codigo), MMIO / Limites frente al mapa EFI (codigo).
Aceptacion: QEMU coteja los registros y la pagina F3. METAL muestra motores SATA activos en puertos 4 y 5 y NVMe habilitado, ambos con BME.
Pendiente: Completar la reanudacion con colas propias y probar el traspaso en METAL antes de activar AMD-Vi.

## kernel/drivers/storage/quiesce.inc

Detiene motores AHCI y solicita el cierre normal NVMe en el banco virtual antes de retirar BME.

Estado: QEMU. Anillo: 0. Lenguaje: ASM x86-64.
Entrada: Captura post-EBS, BAR validado, identidades PCI del banco y AMD-Vi de TCG desactivado.
Salida: Parada confirmada de ambos controladores e informes HID posteriores. El banco solo emite imagen QEMU.
Depende de: Almacenamiento / Estado posterior a UEFI (codigo).
Aceptacion: QEMU coteja los registros vivos, confirma SHST y que BME se retira, y verifica omision cuando falta AMD-Vi.
Pendiente: Reanudar AHCI y NVMe con colas propias y lecturas traducidas antes de ensayar en METAL.

## tools/boot/amdvi_ahci.py

Comprueba READ DMA EXT desde AHCI emulado en un dominio AMD-Vi separado, junto con xHCI y EDU.

Estado: QEMU. Anillo: host. Lenguaje: Python.
Entrada: Disco determinista del banco, reserva del invitado e IOVA mapeada por Ring 0.
Salida: Dos lecturas verificadas del mismo sector y testigo fisico de la IOVA intacto, con informes USB en ambas etapas.
Depende de: AMD-Vi / Dominios en el invitado (verificacion).
Aceptacion: QEMU verifica 512 B por lectura y ausencia de fallos IOMMU durante AHCI antes y despues de invalidar EDU.
Pendiente: Sustituir el banco AHCI dirigido por HOST por una lectura desde el driver nativo y verificarla en METAL.

## tools/boot/amdvi_nvme.py

Cierra las colas de OVMF, instala colas NVMe del laboratorio y lee en un cuarto dominio AMD-Vi administrado por Ring 0.

Estado: QEMU. Anillo: host. Lenguaje: Python.
Entrada: Namespace virtual determinista, BAR validado y cinco IOVA para colas y datos.
Salida: Dos lecturas traducidas del mismo sector junto a SATA y USB. Medio exclusivo de QEMU.
Depende de: AMD-Vi / Lectura SATA traducida en QEMU (codigo).
Aceptacion: Cotejar completados, 512 B por lectura, testigo de las IOVA, cierre de NVMe y ausencia de fallos IOMMU nuevos.
Pendiente: Ejecutar el traspaso y verificar NVMe en METAL antes del arranque de GSP.

## kernel/drivers/storage/nvme_guest.inc

Crea CQ1 y SQ1, lee un sector en el dominio 4, confirma cierre y revoca su ventana temporal.

Estado: QEMU. Anillo: 0. Lenguaje: ASM x86-64.
Entrada: NVMe emulado quiescente, AMD-Vi activo y reserva de cinco IOVA de cola y datos.
Salida: Tres completados, 512 B traducidos y permiso DMA retirado al cerrar.
Depende de: AMD-Vi / Lectura NVMe traducida en QEMU (verificacion), AMD-Vi / Dominios en el invitado (codigo), MMIO / Limites frente al mapa EFI (codigo).
Aceptacion: Leer dos veces en QEMU con HID activo y rechazar solicitudes sin dominio o con EDU todavia habilitado.
Pendiente: Trasladar a METAL la propiedad de las colas y el traspaso de firmware.

## kernel/drivers/bus/mmio_range.inc

Comprueba la geometria del mapa y rechaza que una ventana MMIO invada una region EFI de memoria.

Estado: QEMU. Anillo: 0. Lenguaje: ASM x86-64.
Entrada: Rango fisico alineado y mapa EFI final en la entrega de arranque.
Salida: Aprobacion del rango para una ventana temporal del supervisor.
Depende de: contrato propio sin dependencias en este catalogo.
Aceptacion: Las sondas de almacenamiento comparten la guarda. El binario de lectura METAL conserva sus bytes.
Pendiente: Extender la comprobacion al backend NVIDIA post-EBS al abrir sus recursos propios.

## CASM

Lenguaje y codificador propio x86-64: metal64, Native y su futura ampliacion privilegiada.

Estado: base HEREDADA; banco metal64 HOST. Ver STATUS-BMO-X2.md para los perfiles y limites.

## kernel

Fuentes y evidencias de mecanismos Ring 0; extensiones experimentales del puente declaradas por perfil.

El backlog unico esta en docs/RING0-PLAN.md. Consultar el estado y la evidencia de cada nodo activo.

## userspace

Bibliotecas, servicios, drivers y aplicaciones de Ring 3.

Crates y perfiles HOST/QEMU existentes no acreditan aun todos los procesos y servicios aislados del diseno.

## super-grafo

Mesa de trabajo: catalogo, notas, posiciones y fotografia real del analizador.

166 nodos del catalogo; relaciones de codigo y de plan distinguidas por clase.
