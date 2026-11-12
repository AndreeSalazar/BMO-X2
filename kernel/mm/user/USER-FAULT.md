# Fallo de proteccion desde CPL3

```powershell
.\bmo-x2.ps1 -Accion aislamiento
.\bmo-x2.ps1 -Accion aislamiento -Cpu Nehalem
```

CASM instala tablas propias, GDT, TSS e IDT. IRETQ inicia el programa
fijo en `0x40000000`, con codigo RX y pila RW+NX. El programa escribe
una marca en su pila e intenta leer `0x100000` en el mapa supervisor.
La CPU genera el vector 14 con codigo 5, carga RSP0 desde la TSS y
entrega el marco de excepcion a Ring 0. El manejador reconstruye sus
punteros desde la pila de Ring 0 y verifica la direccion, el RIP y la
marca. Desmapea ambas paginas de usuario, invalida sus traducciones y
borra los 8192 bytes antes de detenerse en CPL0.

QEMU verifica CR2, CS, el marco hardware, la puerta, la TSS, las tablas
finales y el borrado. El caso con RDI nulo conserva el CR3 y la pila
heredados. La prueba usa 32 KiB dentro de la reserva del puente,
incluidas cinco tablas, dos paginas de usuario y una de descriptores
y pila de excepcion. La reserva se usa en un ensayo terminal con un
programa conocido. La devolucion a un asignador general, el planificador
y la reanudacion con un segundo proceso siguen pendientes.

El perfil tiene 716 bytes de cuerpo y un paquete de demostracion de
740 bytes. El limite de este ensayo es la pagina de 4096 bytes del
puente. El contrato de entrada compacta conserva su limite menor de
512 bytes.

[Fuente](main.casm) | [Vector](expected.hex) | [Evidencia](evidence.json)
