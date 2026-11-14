# ULTRA-J 0.1

ULTRA-J toma de Java la escritura con clases y tipos declarados. El perfil
HOST incluye un compilador inicial para el ciclo de una region. El
escritorio asigna el aspecto por clase con un tema independiente.

## Sintaxis de la sonda

Se admite una clase con un metodo `void run()`, bloques
`try (Region r = new Region(id))`, expresiones `new Window();` y
`new Button();` dentro de los bloques, y un `return;` final.
El cierre del bloque representa `CLOSE`. Los nombres de la clase y de
la variable de region se consumen durante la compilacion. El formato
v1 conserva los IDs y las instrucciones. Espacios y comentarios no
alteran los bytes del programa.

El perfil v2 agrega variables locales `Window panel = new Window();`
y `Button enter = new Button();`. Los metodos incorporados
`panel.show();` y `enter.activate();` operan sobre su instancia.
Los nombres solo existen durante la compilacion y su alcance termina
al cerrar la region. Las llamadas emiten v2. Los programas del perfil
original conservan sus bytes v1.

## Sintaxis prevista

| Conservar de Java | Acotar para el primer lenguaje |
|---|---|
| `class`, `interface`, `implements`, visibilidad, constructores y metodos | Composicion e interfaces. Cada tipo, campo y metodo recibe un indice durante el enlace. |
| `new`, `this`, tipos escalares, referencias tipadas y control de flujo | Una asignacion tiene un propietario de region. Las referencias entre objetos de una misma region pueden formar ciclos. |
| Metodos de objetos para eventos | Una aplicacion solicita superficies y eventos a DIRECTOR mediante capacidades. |

Se aplazan `extends` entre clases, genericos, lambdas, excepciones,
reflexion y carga dinamica de clases. Los escalares se guardan por valor.
Los nombres resueltos pueden viajar en un mapa de diagnostico externo.

Ejemplo de la sintaxis futura de aplicacion:

```java
class Panel implements View {
    private int clicks = 0;

    public void onClick() {
        this.clicks = this.clicks + 1;
    }
}
```

## Binarios del perfil HOST

Los dos archivos empiezan con ocho bytes. Los enteros multibyte son
little-endian. Byte 4 indica la version y byte 5 contiene flags `00`.
UJBC admite versiones 1 y 2. UJTH usa version 1.
Los opcodes son de ULTRA-J. Su significado y sus datos se conservan
en cualquier destino. El codigo de maquina y el ABI del sistema
pertenecen al presentador o a la VM de cada arquitectura.

**`.ujb`** usa la firma ASCII `UJBC`. Los bytes 6 y 7 indican la longitud
exacta de las instrucciones, de 1 a 4096 bytes. El cuerpo es lineal.

| Bytes | Efecto |
|---|---|
| `10 rr` | Abre la region `rr` de 1 a 255. Solo puede haber una activa. |
| `20 cc` | Crea un objeto de clase `cc` en la region activa. La clase `01` (Window) ocupa 32 bytes y `02` (Button) ocupa 16. |
| `30 rr` | Cierra la region activa si coincide con `rr` y vuelve a entregar el espacio de objetos a la arena. |
| `40 ss mm` | En v2, llama al metodo `mm` sobre el objeto de indice `ss` en orden de reserva desde cero. |
| `FF` | Retorna con la region cerrada. Debe ser el ultimo byte. |

Cada objeto de la sonda empieza con su ID de clase seguido por bytes a
cero. La arena tiene 256 bytes y reserva de forma consecutiva. El cierre
restablece el cursor en una operacion, sin recorrer los objetos. Cada
nueva reserva inicializa su rango antes de usarlo. Liberar el espacio
dentro de la arena y devolver paginas al kernel son operaciones distintas.
El verificador exige que el receptor exista en la region activa y que
el metodo corresponda a su clase. `01` es Window.show y `02` es
Button.activate. En HOST ambos ponen a uno el byte de estado de la
instancia, en el offset 1 del objeto. La llamada carece de salida grafica.
El perfil actual carece de campos de referencia y recursos externos. Antes de
agregarlos, el verificador debe impedir que un objeto de vida mas larga
retenga referencias a una region mas corta. Las superficies y archivos
se cierran por sus propios contratos.

**`.ujt`** usa la firma ASCII `UJTH`. Los bytes 6 y 7 indican dos
registros de 12 bytes, ordenados por ID de clase. Cada registro incluye
ID, radio, relleno y un byte reservado a cero, seguidos de fondo y texto
como dos valores `u32` de la forma `0x00RRGGBB`. Radio y relleno se
expresan en pixeles logicos de 0 a 32. Esta tabla cumple el papel de un
tema al estilo CSS. Los selectores, las reglas de cascada y el dibujo
pertenecen a etapas posteriores.

## Evidencia y frontera

El [banco HOST](runtime.py) verifica el binario y el tema
completos antes de aplicar la secuencia. Reporta errores con codigo,
campo y offset. Los [vectores exactos](README.md)
prueban una ventana, dos botones, cierre y reuso desde el offset cero.

El siguiente hito es una VM en Ring 3 con el mismo contrato y un
adaptador para DIRECTOR. Ring 0 carga el ejecutable x86-64 de la VM
mediante SBEF y atiende INVOKE y WAIT.

La autocompilacion requiere expresar el lexer, el parser y el emisor en
ULTRA-J. El primer criterio sera construir ese compilador con el
compilador inicial y comprobar que dos generaciones sucesivas produzcan
el mismo binario a partir del mismo fuente.
El siguiente tramo requiere metodos de usuario, argumentos, control de
flujo y buffers de bytes acotados. Con ellos el compilador escrito en
ULTRA-J podra leer y emitir UJBC mediante servicios explicitos de HOST.

[Referencia de clases de Java](https://docs.oracle.com/javase/specs/jls/se26/html/jls-8.html)
