# Espacios de trabajo del escritorio

El servicio de escritorio de Ring 3 toma las decisiones de ventanas y
foco. El supervisor de sesion inicia y recupera el servicio. El
planificador de Ring 0 administra CPU y el subsistema de entrada entrega
eventos mediante las interfaces concedidas.

El perfil inicial ofrece cuatro espacios numerados. La referencia de
Ultra-LinuX es `src/rootfs/desktop/hyprland.lua`, revision `7c275c1`,
que usa Super con numeros para enfocar y Super+Shift para mover ventanas.

| Atajo | Operacion |
|---|---|
| Super+1, Super+2, Super+3, Super+4 | Cambiar el espacio visible y restaurar su ultimo foco disponible. |
| Super+Shift+1, Super+Shift+2, Super+Shift+3, Super+Shift+4 | Mover la ventana activa al espacio indicado y conservar el espacio visible. |

Cambiar de espacio conserva los procesos y las ventanas de los demas
espacios. Si se cerro la ventana enfocada, se usa la siguiente ventana
disponible de ese espacio. Los cuatro espacios forman el primer perfil
de prueba.

La primera comprobacion abre dos clientes, cambia el foco entre espacios
y mueve una ventana. El test comprueba que ambos clientes siguen vivos
y que volver a un espacio restaura el foco. El servicio queda en diseno.
La politica de ventanas de Director se sustituye por este contrato. Las
demas responsabilidades del padre se auditan como servicios por separado.
