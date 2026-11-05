# Las listas y la jerarquia de CASM

El destino de desarrollo es el kernel Ring 0 x86-64. El alcance actual y una
lectura byte a byte se explican en [RING0](contracts/RING0.md). Cada compilacion
Windows aceptada agrega `HEX.md` tras repetir la verificacion y comprobar el paquete.
Para releer un run: `bmo-x2.ps1 -Accion leer-hex -Run build/CASM/run-...`.

`catalog.json` declara el perfil activo `metal64-0.2` para x86-64. Sus 45
elementos forman un arbol con tres estados: implemented, partial y planned.

```text
CASM
  compiler
    source
    frontend -> lexer, symbols, integers, grammar
      grammar -> entry, strings, integers, puts, put-int, return
    model -> types (8), IR (4 formas)
    encoding -> LEA RIP relativo, CALL de servicio, RET
    HEX -> verification -> packet
    tests
  kernel-profile -> memoria, MMIO, privilegios, excepciones, Ring 3, imagen
  native-profile -> experiencia heredada, con su contrato separado
```

El recorrido ejecutado por el compilador sigue la cadena de `pipeline`:
fuente -> frontend -> IR -> codificador -> HEX -> verificacion -> paquete.
Las ramas del perfil de kernel marcadas planned todavia no aceptan instrucciones.

## Una lista que alimenta codigo real

`catalog.py generate` valida el arbol y genera `src/model/types.c` desde los
ocho tipos declarados. Windows y Linux invocan ese paso antes de construir.
Los cambios del catalogo y su generador tambien invalidan la cache del build.

El verificador conserva `INT_TYPES` escrito por separado. Una discrepancia
de anchura o signo impide generar. Las tres codificaciones declaradas se
contrastan con el vector manual `kernel/boot/fixtures/entry.hex`. El catalogo
no genera las plantillas del verificador ni acredita toda la ISA x86-64.

Cada compilacion conserva una copia de `catalog.json` junto a fuente, IR,
HEX y herramientas. El mapa corresponde a la fuente congelada de ese run.

## Consultarlo con SUPER GRAFO

```powershell
.\bmo-x2.ps1 -Accion consultar -Consulta casm
.\bmo-x2.ps1 -Accion consultar -Consulta casm -Argumentos '{"seccion":"jerarquia","id":"frontend","limite":12}'
.\bmo-x2.ps1 -Accion consultar -Consulta casm -Argumentos '{"seccion":"tipos"}'
.\bmo-x2.ps1 -Accion consultar -Consulta casm -Argumentos '{"seccion":"formas"}'
.\bmo-x2.ps1 -Accion consultar -Consulta casm -Argumentos '{"seccion":"codificaciones"}'
.\bmo-x2.ps1 -Accion consultar -Consulta casm -Argumentos '{"seccion":"reglas","id":"INT-OVERFLOW"}'
.\bmo-x2.ps1 -Accion compilar -Source .\kernel\boot\entry.casm
.\bmo-x2.ps1 -Accion consultar -Consulta casm -Argumentos '{"seccion":"mapa","ruta":"kernel/boot/entry.casm"}'
```

En la ventana de SUPER GRAFO, el **Taller CASM** muestra el arbol interactivo,
tipos, campos de IR y patrones de bytes. Cada fuente declarada se abre desde
su nodo. **Releer listas** actualiza desde disco; guardar en el editor tambien
invalida la vista. Las condiciones originales de rechazo se leen de los modulos
de `sources.json`, incluyendo las llamadas tipadas `CASM_RULE_*`.

Las consultas llevan limite y cuentan lo omitido. El mapa da linea, offset del
cuerpo, offset del paquete y bytes. Si cambia la fuente sin recompilar, no
devuelve el mapa viejo. Los datos largos muestran cuantos bytes se omitieron.
Tambien se contrasta el paquete FAGRAW64 completo con el HEX y los campos
basicos de `verified.json`. Esto comprueba consistencia de artefactos; no
autentica el reporte ni ejecuta el codigo de destino.

## Ampliar el lenguaje

Una capacidad nueva necesita estado y lugar en el arbol, semantica, IR,
codificacion propia, verificacion independiente y pruebas de aceptacion y
rechazo. Solo entonces pasa a implemented. El dibujo organiza y explica;
la aceptacion del compilador se gana en codigo y con evidencia.
