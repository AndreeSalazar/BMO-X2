# Genesis G0: ver cada byte antes del despertar

La primera entrega imprime `GENESIS` y retorna al cargador metal64. Se compila
en el anfitrion; no arranca sola ni sustituye firmware, pila o contexto.

```powershell
.\bmo-x2.ps1 -Accion genesis
```

El run conserva fuente, catalogo, herramientas, IR, HEX, paquete, `HEX.md` y
`genesis.json`. El verificador independiente vuelve a comprobar la emision;
el guardian Genesis exige el vector manual y un paquete menor de 512 bytes.

| Cuerpo | Bytes | Motivo |
|---|---|---|
| 0..6 | 48 8D 35 05 00 00 00 | Direccion del mensaje en RSI: 7 + 5 = offset 12. |
| 7..10 | 41 FF 57 10 | Servicio puts de la tabla R15, desplazamiento 16. |
| 11 | C3 | Retorno al cargador. |
| 12..21 | 47 45 4E 45 53 49 53 0D 0A 00 | GENESIS, CR/LF y NUL. |

Resultado esperado: 12 bytes de instrucciones + 10 de datos = 22 de cuerpo;
24 de cabecera + 22 = 46 de paquete. La representacion textual HEX ocupa
otro tamano. Los costes del cargador y del compilador no estan en esos 46.

La reduccion frente al saludo anterior viene del mensaje mas corto; las
instrucciones siguen ocupando 12 bytes. No se presenta como una optimizacion
de la misma salida ni como una medida de energia.

## Nodos y colores con motivo

La configuracion vive en `super-grafo/genesis.json`; se aplica mediante
`tools/genesis_graph.py` sobre `super-grafo/orden.json`, sin borrar las otras
posiciones. Flujo vertical inspirado en Houdini; no es un archivo de Houdini.
La apertura enfoca Genesis para leer fuente, vector, evidencia y contrato.
Salir del foco permite explorar los otros nodos del compilador; no se intenta
mostrar todo el proyecto expandido en una sola pantalla.
La disposicion se fija al aplicar Genesis. Los estilos y posiciones ya guardados
se conservan; `tools/genesis_graph.py --reset` restaura los declarados. En SUPER
GRAFO, seleccionar un nodo habilita **Estilo del nodo**: color, motivo y forma
urbana con vista previa y guardado automatico. Los textos completos se leen
en la ficha; no desbordan la tarjeta. Los cables de este foco representan
pertenencia a carpetas, no pasos de ejecucion.

- Cian: fuente, lo que se solicita.
- Azul: frontend y modelo, interpretacion y tipos.
- Violeta: emisor, donde se deciden los bytes.
- Dorado: vector manual, referencia que el emisor no genera.
- Verde: verificador, responsabilidad de contrastar, no sello automatico de exito.
- Blanco: evidencia y explicacion del resultado.

Cada nota dice entrada, salida, aceptacion y lo que falta. Los cables del
analizador siguen siendo dependencias que puede extraer; las relaciones
conceptuales de etapas se declaran en el catalogo y no se inventan imports.

G1 pendiente: repetir el contexto del puente en QEMU, observar CPL y mensaje,
y comprobar la carga exacta. Despues: excepciones y mecanismos CASM propios.
