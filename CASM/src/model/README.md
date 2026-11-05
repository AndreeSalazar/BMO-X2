# Modelo privado del compilador anfitrion

`types.c` declara las anchuras y nombres de los tipos metal64.
`storage.c` administra dos depositos dentro de un `CasmProgram` de direccion
estable. No hay asignaciones por elemento ni dependencia del runtime del destino.

Los punteros a datos y RPN son privados del anfitrion. No viajan a la IR JSON
ni a HEX. Un programa se inicializa en cero por compilacion, no se mueve ni se
copia mientras se usan sus punteros. Se libera como un solo bloque al terminar.

## Por que caben las fuentes admitidas

- La fuente tiene como maximo 65.536 bytes; la entrada publica lo comprueba.
- Datos: caracteres decodificados de cadenas no superan su fuente. Cada una
  de las 128 constantes puede agregar NUL o representar un decimal de hasta
  21 caracteres mas NUL. El deposito de datos reserva fuente + 128 * 24:
  **68.608 bytes**. Se conserva el rechazo BODY-LIMIT del payload en el emisor.
- RPN: cada referencia agrega `@` y separador; cada negacion puede pasar de
  `-` a `neg` mas separador; operadores y decimales canonicos tambien caben
  en cuatro veces sus caracteres de fuente. Se agrega como maximo un NUL por
  entero. Deposito: 4 * 65.536 + 128 = **262.272 bytes**.
- Siguen vigentes los limites por expresion: 256 tokens, 32 niveles y 4.096
  caracteres de RPN. Compartir almacenamiento no los elimina.

Cada escritura comprueba el espacio restante antes de modificarlo. Una
expresion finalizada conserva su texto: solo la expresion actual agrega bytes.
El banco C cubre extremos, contadores fuera de limite, estabilidad y rechazo
sin escritura parcial. La comparacion con d2575a8 cubre fuentes densas y los
mismos rechazos, para que un deposito mas chico no cambie el lenguaje.

La medida `sizeof(CasmProgram)` es memoria declarada del modelo anfitrion.
No incluye RSS, sobrecoste del asignador, pila de llamadas, fuente o verificador,
y no representa la RAM del futuro kernel.
