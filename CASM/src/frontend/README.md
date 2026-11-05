# Frontend metal64: una responsabilidad por modulo

| Archivo | Pregunta que responde |
|---|---|
| `lexer.c` | Que token y posicion hay en la fuente acotada. |
| `symbols.c` | Que nombres estan reservados, declarados y asociados a tipos. |
| `integers.c` | Que valor exacto tiene una expresion y donde debe rechazarse. |
| `parser.c` | Como se forma una declaracion, llamada y entrada del perfil. |
| `internal.h` | Que estado e interfaces comparten estos modulos del anfitrion. |

`../frontend.c` conserva la entrada publica y el despacho REAL de diagnosticos.
Los modulos pasan regla, motivo y posicion; el despacho imprime el rechazo.
El Taller de SUPER GRAFO lee `sources.json` y reconoce las llamadas tipadas
`CASM_RULE_*`. Muestra primero la condicion original en su modulo y conserva
tambien el sitio del despacho. Los casos aislados se extraen de las pruebas.

No se cambio la gramatica metal64 0.2. Native conserva su perfil y sus
pruebas Linux separadas. El reparto permite ampliar el lenguaje sin mezclar
lexer, reglas numericas, almacenamiento y emision de instrucciones.
