# Audio de BMO-X2

El padre resolvio la salida USB y el sonido de DOOM con bancos de
efectos, voces y contadores de cortes. Su adaptador tambien renderiza
musica FM usando GENMIDI del WAD. BMO-X2 toma la reproduccion
independiente del bucle del juego y los contadores de cortes.
La mezcla y los formatos viven en Rust Ring 3. El transporte y la
autoridad sobre el dispositivo quedan en CASM Ring 0.

## Controles

| Control | Alcance | Estado |
|---|---|---|
| Volumen general y silencio | Salida mezclada | HOST |
| Ganancia y balance | Cada fuente | HOST |
| Picos y muestras saturadas | Cada bloque mezclado | HOST |
| Efectos y musica por separado | Dos fuentes de DOOM con niveles propios | Diseno |
| Selector de salida y latencia | Elegir dispositivo y tamanos admitidos | Diseno |
| Cortes, cola y desconexion | Contadores del dispositivo publicados por Ring 0 | Diseno |

El mezclador acepta PCM estereo i16 a una frecuencia comun, hasta 16
fuentes y buffers prestados por el llamador. Completa con silencio
cuando una fuente termina. Aplica la ganancia general antes de
saturar y cuenta las muestras saturadas. El medidor usa el valor
absoluto de cada canal. La mezcla usa memoria fija por bloque y
el llamador conserva la propiedad de sus buffers.

Desde la raiz, ejecutar las tres pruebas HOST:

```powershell
New-Item -ItemType Directory -Force build/audio | Out-Null
rustc --edition=2024 --test -D warnings userspace/services/audio/src/lib.rs -o build/audio/audio-tests.exe
.\build\audio\audio-tests.exe
```

## Integracion

1. **QEMU, salida virtual.** Empezar con Intel HDA y un codec de solo
   salida. Capturar PCM en WAV y comprobar muestras, canales y silencio.
   AC97 queda como segunda opcion para una comparacion de transporte.
2. **Ring 0, propiedad y plazos.** Reservar una cola acotada de buffers
   del dispositivo. Aceptar bloques por una capacidad INVOKE y publicar
   finalizaciones. Reutilizar marcos solo tras confirmar la parada y
   revocacion. Seguir el [contrato DMA](../../../kernel/drivers/bus/DMA.md).
3. **Ring 3, servicio y escritorio.** Programar la mezcla fuera del
   bucle del juego. Dar al escritorio control de volumen, silencio y
   seleccion de salida. Medir cortes y ocupacion de cola antes de
   reducir el buffer. A 48 kHz, un bloque candidato de 240 marcos
   ocupa 960 bytes y dura 5 ms. Esa duracion cubre un bloque.
4. **DOOM.** Adaptar efectos y musica a fuentes distintas. La primera
   prueba audible reproduce un efecto mientras el juego deja de
   producir cuadros. Luego probar musica, balance y mute por separado.
5. **Metal.** Probar USB Audio Class con el auricular que usaba el
   padre, tras descubrir sus formatos y su reloj. Desarrollar la ruta
   USB sobre el bus xHCI propio y validar desconexion y recuperacion.

La primera salida requiere que un SBEF externo llegue a CPL3. El
mezclador ya se prueba en HOST. El dispositivo, la cola y el adaptador
de DOOM quedan pendientes.
