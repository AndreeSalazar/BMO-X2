# CONTROL, RENDIMIENTO y ELEGANCIA

## Control

Una sola arquitectura de destino: x86-64. Tipos, efectos, trampas y limites
deben ser explicitos. Emision propia y verificacion independiente antes de
publicar. Una regla que rechaza conserva su caso y su motivo al reorganizarse.

## Rendimiento

Separar recursos del compilador y del destino. El modelo, tiempo de compilar,
memoria real del proceso, bytes emitidos, instrucciones, ciclos y vatios son
medidas distintas. Una mejora declara cual midio, el caso, herramienta y coste.

Primera medida: el modelo HOST baja 66,43 %, de 1.077.280 a 361.648 bytes.
El HEX del destino se conserva. La semilla ejecutable crece 512 bytes en esta
construccion con Clang: es el coste observado del reparto en modulos, no un
ahorro de todo el sistema. No se han medido RSS, energia ni ciclos del kernel.

## Elegancia

Cada nodo responde una pregunta; la interfaz declara lo que cruza. No se
reparte por longitud arbitraria ni se duplican implementaciones para el dibujo.
`sources.json` es la lista de construccion comun a Windows y Linux; sus
cabeceras tambien invalidan la cache de la semilla.

## Reproducir y continuar

```powershell
.\bmo-x2.ps1 -Accion comprobar
.\bmo-x2.ps1 -Accion medir
.\bmo-x2.ps1 -Accion mapa
```

El medidor reconstruye la base `d2575a8` desde Git, compara 333 fuentes y
registra `build/CASM/maturity/report.json`. No ejecuta los programas emitidos.
Hace falta tener ese commit en el historial. El resumen fechado vive en
`metrics/host-maturity.json`.

Lo que sigue para Ring 0 sigue abierto en `x86_64/requirements.json`:
memoria, efectos privilegiados, excepciones, carga y entrada en Ring 3.
Esta mejora cierra el reparto y el almacenamiento de la semilla metal64 en
HOST; no declara completo el lenguaje del kernel ni su autocompilacion propia.
