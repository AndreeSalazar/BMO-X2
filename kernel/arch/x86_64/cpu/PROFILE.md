# Identificacion x86-64

`identify.casm` activa el perfil cerrado `ring0-cpu-0.1`. CASM emite
`FA 31 C0 0F A2 F4 EB FD`, con 8 bytes de cuerpo y 32 de paquete.
El limite de entrada de 512 bytes deja un margen utilizable de 479.
`identify.hex` es el vector manual que usa el guardian. El HEX generado
se conserva como `program.hex` en el run.

La sonda ejecuta CPUID hoja 0 y deja sus resultados en los registros
antes de detener la CPU. El banco QEMU comprueba que se ejecutaron los
bytes verificados tras ExitBootServices, en Ring 0, y que RIP quedo
dentro de la parada propia. El guardian coteja la captura con el informe
y genera `profile.config` en el mismo run. El fabricante y la hoja
basica maxima salen de los registros de la CPU invitada. El archivo
registra tambien la huella del paquete.

QEMU devolvio `AuthenticAMD` con hoja maxima 13 en `qemu64` y
`GenuineIntel` con hoja maxima 11 en `Nehalem`, con el mismo paquete.
[Capturas de registros y perfiles](evidence.json).

```powershell
.\bmo-x2.ps1 -Accion detectar
.\bmo-x2.ps1 -Accion detectar -Cpu Nehalem
```

El perfil observado pertenece a esa ejecucion QEMU. El kernel aun no
consume el archivo. La aplicacion del perfil requiere descubrir las
capacidades necesarias, validar los recursos del contexto de arranque
y seleccionar opciones seguras antes de inicializar cada subsistema.

## Geometria L1 en el perfil de escritorio

[cache_profile.inc](cache_profile.inc) consulta CPUID en el procesador de
arranque. El contexto conserva la hoja, los descriptores presentes
y los campos crudos de geometria en `0xD0..0xEF`. Una entrada ausente
se publica como `unknown` en el `profile.config` que genera el ensayo
QEMU. Se vuelve a consultar en cada arranque. El archivo documenta
el resultado y el presupuesto de la puerta. La fuente de datos en
ejecucion es el contexto, y el ensayo actual usa un solo CPU.

La geometria sirve para medir el margen de codigo. Los mapeos SBEF
de Ring 3 se respaldan con marcos de RAM. La CPU puede almacenar en
cache instrucciones y datos de ambos anillos durante la ejecucion.
La politica por nucleo y las mediciones en metal siguen pendientes.
