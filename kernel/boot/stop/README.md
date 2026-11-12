# Primera parada propia: S1

`main.casm` usa el perfil cerrado `ring0-stop-0.1`:

```c
void kernel_main(void) {
    cpu_halt();
}
```

El frontend y emisor propios en `CASM/src/kernel/stop.c` aceptan solo esta
gramatica, espacios y comentarios ASCII. No hay retorno, datos ni llamada a
servicios del puente. La IR esquema 3 declara perfil, CPL requerido, efectos y
linea de origen. El modelo y emisor metal64 0.2 permanecen separados.

| Linea | Offset cuerpo | Offset paquete | Bytes | Significado |
|---|---|---|---|---|
| 2 | 0 | 24 | FA | CLI: IF=0, enmascara interrupciones enmascarables. |
| 2 | 1 | 25 | F4 | HLT: detiene este procesador logico. |
| 2 | 2 | 26 | EB FD | Salto relativo -3: vuelve a HLT si la ejecucion continua. |

El vector manual `expected.hex` y `CASM/stop_verify.py` son independientes del
emisor: el verificador vuelve a analizar la fuente, exige todos los campos y
tipos de la IR y contrasta los cuatro bytes antes de publicar el paquete.
El paquete FAGRAW64 ocupa 28 bytes: 24 de cabecera y 4 de codigo. El puente
UEFI heredado ocupa otros 12288 bytes; firmware, disco, paginas y contexto no
estan incluidos en ese presupuesto.

El verificador exige un paquete de menos de 512 bytes antes de publicarlo.
El maximo utilizable es 511 bytes, con hasta 487 de cuerpo. Esta entrada
deja 483 bytes de margen. El informe `HEX.md` muestra el margen y el tamano
del archivo HEX de texto por separado.

```powershell
.\bmo-x2.ps1 -Accion parada
.\bmo-x2.ps1 -Accion compilar -Profile ring0-stop-0.1 -Source kernel/boot/stop/main.casm
.\bmo-x2.ps1 -Accion leer-hex -Run build/CASM/run-...
```

`parada` crea un run nuevo, verifica, ejecuta siete casos en QEMU/OVMF y
publica solo evidencia comprobada en `evidence/`. Las imagenes son archivos
virtuales en `build/`; no se instala nada en discos fisicos. El caso normal
exige BootServices cerrados, copia exacta del cuerpo, CPL0, HLT=1, IF=0,
RIP=entrada+2 y bandera de retorno en cero. Comprueba tambien las reservas
del mapa de memoria y el framebuffer del puente. Los otros seis casos
prueban firma, suma, entrada, ausencia, exceso de paquete y reintentos acotados
de ExitBootServices. No prueban una politica general de interrupciones.

HLT no apaga el equipo. CLI no bloquea NMI, SMI ni reset. Este contrato exige
modo largo y CPL0 y no instala IDT ni manejadores. No acredita ahorro de
vatios, arranque autonomo, otros procesadores ni ejecucion fisica. Referencia:
[Intel SDM, volumen 2, CLI/HLT/JMP](https://www.intel.com/content/www/us/en/developer/articles/technical/intel-sdm.html).

SUPER GRAFO representa la linea 2 en tres tramos (1+1+2 bytes) y rechaza un
perfil, fuente, desplazamiento o instruccion diferente. Los colores guardados
en `super-grafo/orden.json` indican responsabilidades; la evidencia QEMU tiene
su nodo propio. Proximo contrato: contexto y diagnostico propios con una
excepcion controlada antes de habilitar interrupciones.

En Windows, el Taller ofrece **Generar HEX de parada Ring 0** al abrir el
espacio BMO-X2. El boton usa `pwsh.exe` de PowerShell 7 y guarda una nueva
compilacion verificada en `build/CASM`. La accion `parada` ejecuta QEMU por
separado.
