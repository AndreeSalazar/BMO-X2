# IR BMO: frontera entre productores y destinos

Estado: **diseno pendiente de implementacion**. Este contrato fija la
arquitectura deseada del HOST; no declara que el HOST actual acepte todos los
compiladores ni que exista ya un formato binario IR-BMO.

## Objetivo

Unificar la entrada de productores sin llevar sus toolchains ni sus runtimes
a Ring 0. Los adaptadores convierten una fuente o representacion de
compilador admitida a una IR BMO versionada. El HOST valida y normaliza esa
IR, aplica optimizaciones que preserven su semantica y la baja mediante un
backend propio para cada destino.

```text
fuente o IR de productor
  -> adaptador HOST
  -> IR BMO validada
  -> optimizacion semantica
  -> backend de una ISA y ABI
  -> paquete nativo del destino
  -> cargador / NANO-CORE de ese destino
```

La IR BMO es el modelo semantico; su serializacion binaria se especificara
despues de fijar las operaciones y reglas. Su inspiracion es el rol de una IR
de compilador, como el modelo de generacion de codigo de
[LLVM](https://llvm.org/docs/CodeGenerator.html); BMO definira sus propias
operaciones, reglas y codificacion. No depende de LLVM bitcode ni lo instala
en Ring 0. El paquete ejecutable final es distinto y especifico del destino.
Para BMO-X2 actual ese paquete es SBEF x86-64, con el encabezado y perfil ISA
descritos en [SBEF](SBEF.md).

## Limite de entrada

- Una fuente o IR del compilador puede convertirse a IR BMO si un adaptador
  implementa y valida las construcciones usadas.
- Un PE/ELF/COFF que ya contiene codigo maquina se puede admitir para su ISA
  cuando exista un importador y perfil compatibles. Ese codigo no se vuelve
  codigo de otra ISA por cambiar su encabezado.
- La traduccion de un ejecutable nativo ya compilado a otra ISA requeriria un
  traductor binario separado que decodifique instrucciones y recupere su
  semantica. No se presupone en los adaptadores habituales del HOST.
- Los perfiles `x86-64-v1` a `v4` describen requisitos x86-64. No definen las
  operaciones de IR BMO ni un perfil para POWER, Cell, ARM u otra CPU.

## Semantica que debe conservarse

La IR debe expresar explicitamente, al menos, anchura y signo de valores,
desbordamiento, flujo de control, acceso y orden de memoria, atomicos,
llamadas, retorno, errores y dependencias externas. Los intrinsecos propios
de una ISA deben quedar marcados como extensiones de destino. Una optimizacion
puede cambiar la representacion, pero debe conservar el comportamiento
definido dentro del perfil y runtime declarados.

Si una construccion no tiene semantica especificada, excede el perfil o
necesita un servicio no implementado, el HOST la rechaza con diagnostico
identificable. No descarta silenciosamente la operacion ni afirma que un
binario arbitrario quedo "limpio". Cada adaptador registra origen,
versiones/opciones disponibles, features requeridos y evidencia asociada.

## Separacion por destino

Cada backend define su seleccion de instrucciones, registros, convenciones
de llamada, layout, relocaciones y perfil de ejecucion. Cada destino obtiene
un contrato de paquete, ABI, cargador y NANO-CORE propios. Las capas neutrales
del HOST se reutilizan solo cuando preservan la misma semantica; una ISA no
hereda el encabezado de otra.

```text
IR BMO validada
  +-> backend x86-64 -> SBEF x86-64 -> NANO-CORE x86-64
  +-> backend POWER  -> paquete POWER -> NANO-CORE POWER
  +-> backend Cell   -> paquete Cell  -> NANO-CORE Cell
```

Los juegos pueden conservar su logica y recursos si el adaptador puede
representarlos y el destino provee los ABI, runtime, servicios de sistema,
graficos, audio y entrada que requieren. El codigo maquina resultante,
los puentes y el paquete se generan para cada destino. La compatibilidad del
runtime se valida por separado de la traduccion de instrucciones.

## Etapas de admision

1. Congelar el vocabulario y la semantica IR BMO, con casos de oro binarios.
2. Implementar un adaptador inicial y rechazos precisos para las operaciones
   fuera del subconjunto.
3. Bajar la IR mediante el backend x86-64 actual y cotejar salida, ABI y
   comportamiento contra fixtures freestanding y ejecucion QEMU.
4. Validar un productor a la vez; compartir un formato de entrada no certifica
   todos sus lenguajes, bibliotecas ni runtimes.
5. Abrir un destino nuevo solo con backend, ABI, paquete, cargador y
   NANO-CORE propios y evidencia independiente.

El estado actual sigue en las primeras puertas: el HOST admite algunos ELF/PE
x86-64 acotados y hay fixtures concretos, incluido DOOM. La IR BMO, el
adaptador universal y la admision de todos los compiladores **no estan
implementados**. El registro vigente esta en
[HOST](../tools/host/README.md) y en `python -B tools/sbef.py profiles`.
