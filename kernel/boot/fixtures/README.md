# Vector de la primera entrada

`entry.hex` fija el cuerpo esperado de `../entry.casm` en el perfil metal64.
Se escribio desde la secuencia de instrucciones y el mensaje, separado del
HEX emitido: LEA RSI,[RIP+5], CALL [R15+16], RET y los bytes ASCII con NUL.

Tiene 48 bytes. La cabecera FAGRAW64 anade 24: paquete de 72 bytes. Este vector
sirve para detectar cambios de emision; no es una imagen de arranque ni acredita
que se haya ejecutado el codigo en Ring 0.
