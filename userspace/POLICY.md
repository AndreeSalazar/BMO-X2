# Reglas de Ring 3

| Capa | Decide | Entrada y limite |
|---|---|---|
| Runtime | Inicio y fin del programa, adaptadores de lenguaje y ABI | Imagen admitida, pila y capacidades del proceso. |
| Supervisor de sesion | Orden de inicio, dependencias, reinicio y delegacion | Capacidades recibidas y configuracion de la sesion. |
| Servicios | Politica de ventanas, archivos, entrada y otros recursos | Peticiones y capacidades concretas de cada servicio. |
| Aplicaciones | Lenguaje, logica y formatos de datos | Recursos concedidos por sus interfaces. |

Cada servicio declara que ofrece, de que depende y que capacidades
requiere. El supervisor inicia en orden de dependencias. Si un servicio
falla, registra el motivo y aplica la politica de reinicio de ese
servicio. Un cliente recibe autoridad solo mediante una concesion
explicita. Los servicios pueden repartir la autoridad que recibieron.

## Ejecutar un programa

1. El productor compila o adapta el programa al ABI de BMO-X2 y empaqueta
   el ejecutable x86-64 como SBEF.
2. El supervisor solicita su ejecucion. CASM valida version, rangos,
   permisos y entrada, crea el contexto y entrega CPL3.
3. En CPL3, las instrucciones ordinarias corren en la CPU. El programa
   usa el ABI para pedir operaciones protegidas. La CPU entrega al
   kernel las excepciones que se produzcan.
4. Los rechazos de admision incluyen regla y ubicacion del campo.
   Los fallos de CPU conservan vector, codigo, RIP y, para #PF, CR2.
   Un servicio de diagnostico con capacidad presentara esos registros.

Para Python, se porta el interprete y su runtime como un ejecutable SBEF.
El interprete abre archivos `.py` como datos dentro de Ring 3. El proceso
conserva sus limites de memoria y sus capacidades. Las extensiones nativas
requieren una ruta de carga de usuario compatible con el ABI y los permisos.

## Revision de herencia

Cada crate candidato se revisa en este orden. Primero se fija la revision
y se inspeccionan dependencias directas y transitivas, features, scripts
de build y bibliotecas de plataforma. Luego se registra la interfaz, las
capacidades minimas y el destino HOST o Ring 3. Por ultimo se construye
para BMO-X2 y se prueba su salida y su comportamiento ante falta de permisos
o fallo, segun su rol. El resultado queda en el inventario como evidencia
de reutilizacion, adaptacion o trabajo pendiente.

El [inventario del padre](../heritage/RING3-CRATES.md) registra los
manifiestos revisados. La [politica de ventanas](services/desktop/WORKSPACES.md)
se prueba con clientes pequenos antes de trasladar aplicaciones completas.
## Autoridad por proceso

El perfil de BMO-X2 se organiza por capacidades de alcance explicito.
El supervisor inicia procesos en Ring 3 con los permisos que requiere
cada servicio. La administracion se expresa mediante operaciones
acotadas, sin una cuenta root ni un permiso universal.

La sesion de QEMU separa los permisos de pantalla y entrada. Es un
ensayo de un solo cliente con identificadores fijos. El cargador y el
supervisor deberan asignar capacidades por proceso, limitar su
delegacion y revocarlas al cerrar el recurso o el proceso.
