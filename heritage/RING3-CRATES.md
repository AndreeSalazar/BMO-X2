# Inventario de crates para la transferencia

BMO-X en `6076bdefefc67877419ca53633c6e40cb45fc92d`. Total de paquetes Cargo: **110**.
ABI y admision (4), Aplicacion (7), Biblioteca compartida (61), Medicion (2), Runtime (2), Servicio (3), Toolchain (31).

La familia indica el lugar de origen y el orden de revision. El inventario
recoge dependencias declaradas de compilacion normal, build y target.
La columna ABI marca dependencias directas conocidas. Para admitir un
crate se requieren su cierre transitivo, un build para BMO-X2 y una
prueba de las capacidades del componente. Todos quedan por validar.

| Familia | Crate | Ruta en BMO-X | Dependencias directas | ABI directo |
|---|---|---|---|---|
| ABI y admision | `bmo-abi` | `platform/abi/bmo-abi` | bitflags, bmo-carga-juicio, bmo-disposicion, bmo-hash, bmo-lamina | - |
| ABI y admision | `bmo-bex-gate` | `platform/abi/bmo-bex-gate` | - | - |
| ABI y admision | `bmo-firma` | `platform/abi/bmo-firma` | bmo-cripto | - |
| ABI y admision | `bmo-radiografia` | `platform/abi/bmo-radiografia` | bmo-bex-gate, bmo-carga-juicio, bmo-lente-x86 | bmo-bex-gate |
| Aplicacion | `bmo-app-bankcat` | `Ultra_userspace/apps/bankcat` | bmo-bankcat, bmo-config, bmo-dibujo, bmo-letra-monton, bmo-monton, bmo-userland | bmo-userland |
| Aplicacion | `bmo-app-estudio` | `Ultra_userspace/apps/estudio` | bmo-gpu-ga10x, bmo-monton, bmo-orquesta, bmo-userland, bmo-verrano, bmo-verrano-trama | bmo-userland |
| Aplicacion | `bmo-app-hermes` | `Ultra_userspace/apps/hermes` | bmo-config, bmo-dibujo, bmo-fondo, bmo-letra-monton, bmo-monton, bmo-userland | bmo-userland |
| Aplicacion | `bmo-app-jueces` | `Ultra_userspace/apps/jueces` | bmo-userland | bmo-userland |
| Aplicacion | `bmo-app-ludoteca` | `Ultra_userspace/apps/ludoteca` | bmo-config, bmo-dibujo, bmo-letra-monton, bmo-ludoteca, bmo-monton, bmo-userland | bmo-userland |
| Aplicacion | `bmo-app-proton-x` | `Ultra_userspace/apps/proton-x` | bmo-letra-monton, bmo-monton, bmo-orquesta, bmo-proton-x, bmo-proton-x-casa, bmo-proton-x-sm86, bmo-radiografia, bmo-rtc, bmo-userland | bmo-userland |
| Aplicacion | `bmo-app-taller` | `Ultra_userspace/apps/taller` | bmo-config, bmo-dibujo, bmo-pinta, bmo-rtc, bmo-titan-contrato, bmo-titan-lector, bmo-userland | bmo-userland |
| Biblioteca compartida | `bmo-alarma` | `platform/shared/bmo-alarma` | - | - |
| Biblioteca compartida | `bmo-amplificador` | `platform/shared/bmo-amplificador` | - | - |
| Biblioteca compartida | `bmo-antena` | `platform/shared/bmo-antena` | bmo-lamina | - |
| Biblioteca compartida | `bmo-bankcat` | `platform/shared/bmo-bankcat` | - | - |
| Biblioteca compartida | `bmo-cache-juicio` | `platform/shared/bmo-cache-juicio` | - | - |
| Biblioteca compartida | `bmo-carga-juicio` | `platform/shared/bmo-carga-juicio` | - | - |
| Biblioteca compartida | `bmo-channel` | `platform/shared/bmo-channel` | bmo-lamina | - |
| Biblioteca compartida | `bmo-ciudad` | `platform/shared/bmo-ciudad` | bmo-dibujo | - |
| Biblioteca compartida | `bmo-cola` | `platform/shared/bmo-cola` | - | - |
| Biblioteca compartida | `bmo-config` | `platform/shared/bmo-config` | - | - |
| Biblioteca compartida | `bmo-contadores` | `platform/shared/bmo-contadores` | - | - |
| Biblioteca compartida | `bmo-cripto` | `platform/shared/bmo-cripto` | - | - |
| Biblioteca compartida | `bmo-cubo` | `platform/shared/bmo-cubo` | - | - |
| Biblioteca compartida | `bmo-dibujo` | `platform/shared/bmo-dibujo` | - | - |
| Biblioteca compartida | `bmo-disco-juicio` | `platform/shared/bmo-disco-juicio` | bmo-identify | - |
| Biblioteca compartida | `bmo-dma-forma` | `platform/shared/bmo-dma-forma` | - | - |
| Biblioteca compartida | `bmo-dma-juicio` | `platform/shared/bmo-dma-juicio` | - | - |
| Biblioteca compartida | `bmo-firmware` | `platform/shared/bmo-firmware` | - | - |
| Biblioteca compartida | `bmo-fisica-juicio` | `platform/shared/bmo-fisica-juicio` | - | - |
| Biblioteca compartida | `bmo-foco` | `platform/shared/bmo-foco` | - | - |
| Biblioteca compartida | `bmo-fondo` | `platform/shared/bmo-fondo` | bmo-amplificador | - |
| Biblioteca compartida | `bmo-fraps` | `platform/shared/bmo-fraps` | - | - |
| Biblioteca compartida | `bmo-futex` | `platform/shared/bmo-futex` | - | - |
| Biblioteca compartida | `bmo-golpe` | `platform/shared/bmo-golpe` | - | - |
| Biblioteca compartida | `bmo-hash` | `platform/shared/bmo-hash` | - | - |
| Biblioteca compartida | `bmo-hermes` | `platform/shared/bmo-hermes` | bmo-cripto | - |
| Biblioteca compartida | `bmo-hostile` | `platform/shared/bmo-hostile` | - | - |
| Biblioteca compartida | `bmo-imagen` | `platform/shared/bmo-imagen` | - | - |
| Biblioteca compartida | `bmo-imagen-juicio` | `platform/shared/bmo-imagen-juicio` | - | - |
| Biblioteca compartida | `bmo-juicio` | `platform/shared/bmo-juicio` | - | - |
| Biblioteca compartida | `bmo-lamina` | `platform/shared/bmo-lamina` | - | - |
| Biblioteca compartida | `bmo-lente-gpu` | `platform/shared/bmo-lente-gpu` | - | - |
| Biblioteca compartida | `bmo-lente-x86` | `platform/shared/bmo-lente-x86` | - | - |
| Biblioteca compartida | `bmo-letra` | `platform/shared/bmo-letra` | - | - |
| Biblioteca compartida | `bmo-letra-monton` | `platform/shared/bmo-letra-monton` | - | - |
| Biblioteca compartida | `bmo-ludoteca` | `platform/shared/bmo-ludoteca` | bmo-cripto | - |
| Biblioteca compartida | `bmo-maqueta-cara` | `platform/shared/bmo-maqueta-cara` | - | - |
| Biblioteca compartida | `bmo-mmio-juicio` | `platform/shared/bmo-mmio-juicio` | - | - |
| Biblioteca compartida | `bmo-monton` | `platform/shared/bmo-monton` | - | - |
| Biblioteca compartida | `bmo-msr-lista` | `platform/shared/bmo-msr-lista` | - | - |
| Biblioteca compartida | `bmo-orquesta` | `platform/shared/bmo-orquesta` | - | - |
| Biblioteca compartida | `bmo-pase-gpu` | `platform/shared/bmo-pase-gpu` | bmo-lamina | - |
| Biblioteca compartida | `bmo-pila` | `platform/shared/bmo-pila` | bmo-cripto | - |
| Biblioteca compartida | `bmo-pinta` | `platform/shared/bmo-pinta` | bmo-letra, bmo-maqueta-cara | - |
| Biblioteca compartida | `bmo-prestamo-juicio` | `platform/shared/bmo-prestamo-juicio` | - | - |
| Biblioteca compartida | `bmo-prometeo` | `platform/shared/prometeo` | - | - |
| Biblioteca compartida | `bmo-proton-x` | `platform/shared/proton-x` | bmo-prometeo, bmo-verrano-trama | - |
| Biblioteca compartida | `bmo-proton-x-casa` | `platform/shared/proton-x-casa` | bmo-proton-x | - |
| Biblioteca compartida | `bmo-proton-x-sm86` | `platform/shared/proton-x-sm86` | bmo-bsf, bmo-gpu-ga10x, bmo-hash, bmo-proton-x, bmo-sm86 | - |
| Biblioteca compartida | `bmo-puerta-red` | `platform/shared/bmo-puerta-red` | bmo-lamina | - |
| Biblioteca compartida | `bmo-raiz-juicio` | `platform/shared/bmo-raiz-juicio` | - | - |
| Biblioteca compartida | `bmo-registro` | `platform/shared/bmo-registro` | - | - |
| Biblioteca compartida | `bmo-ritmo` | `platform/shared/bmo-ritmo` | - | - |
| Biblioteca compartida | `bmo-sm86` | `platform/shared/bmo-sm86` | - | - |
| Biblioteca compartida | `bmo-sonido` | `platform/shared/bmo-sonido` | - | - |
| Biblioteca compartida | `bmo-titan-contrato` | `platform/shared/titan-contrato` | - | - |
| Biblioteca compartida | `bmo-titan-lector` | `platform/shared/titan-lector` | bmo-titan-contrato | - |
| Biblioteca compartida | `bmo-usbred` | `platform/shared/bmo-usbred` | - | - |
| Biblioteca compartida | `bmo-verrano` | `platform/shared/verrano` | bmo-lamina, bmo-lente-gpu | - |
| Biblioteca compartida | `bmo-verrano-ayni` | `platform/shared/verrano-ayni` | - | - |
| Biblioteca compartida | `bmo-verrano-trama` | `platform/shared/verrano-trama` | bmo-prometeo, bmo-verrano | - |
| Medicion | `bmo-medida-coste` | `Ultra_userspace/medida/coste` | bmo-juicio, bmo-userland | bmo-userland |
| Medicion | `bmo-medida-sombra` | `Ultra_userspace/medida/sombra` | bmo-bsf, bmo-spirv-front, bmo-spirv-x86-64, bmo-userland | bmo-userland |
| Runtime | `bmo-rt` | `toolchain/lang/base/bmo-rt` | bmo-abi, bmo-monton | bmo-abi |
| Runtime | `bmo-userland` | `Ultra_userspace/userland` | bmo-dibujo, bmo-letra, bmo-pinta, bmo-puerta-red | - |
| Servicio | `bmo-service-director` | `Ultra_userspace/services/director` | bmo-antena, bmo-bankcat, bmo-bsf, bmo-config, bmo-contadores, bmo-cubo, bmo-dibujo, bmo-foco, bmo-fondo, bmo-fraps, bmo-golpe, bmo-gpu-ga10x, bmo-hash, bmo-imagen, bmo-iommu-amdvi, bmo-juicio, bmo-lamina, bmo-nvidia-gsp-control, bmo-pase-gpu, bmo-pila, bmo-radiografia, bmo-registro, bmo-ritmo, bmo-rtc, bmo-sonido, bmo-userland, bmo-verrano | bmo-userland |
| Servicio | `bmo-service-input` | `Ultra_userspace/services/input` | bmo-userland | bmo-userland |
| Servicio | `cabina-core` | `platform/services/cabina-core` | bmo-lamina | - |
| Toolchain | `bmo-antena-movil` | `toolchain/tools/antena/movil` | bmo-antena | - |
| Toolchain | `bmo-atlas` | `toolchain/tools/bmo-atlas` | bmo-letra | - |
| Toolchain | `bmo-bex-link` | `toolchain/tools/bex-link` | bmo-abi, bmo-lente-x86 | bmo-abi |
| Toolchain | `bmo-enlazar` | `toolchain/tools/bmo-enlazar` | bmo-abi, bmo-verify | bmo-abi |
| Toolchain | `bmo-espejo` | `toolchain/tools/espejo` | bmo-c-x86-64, bmo-cpp-x86-64, bmo-enlazar, bmo-lower | - |
| Toolchain | `bmo-espejo-cara` | `toolchain/tools/espejo-cara` | bmo-bankcat, bmo-dibujo, bmo-fondo, bmo-huesped, bmo-imagen, bmo-letra, bmo-pinta, bmo-rtc, bmo-titan-contrato, bmo-titan-lector | - |
| Toolchain | `bmo-espejo-cobol` | `toolchain/tools/espejo-cobol` | bmo-cobol-front, bmo-cobol-x86-64, bmo-lower | - |
| Toolchain | `bmo-estratos-fmt` | `toolchain/tools/estratos-fmt` | bmo-estratos, bmo-hash | - |
| Toolchain | `bmo-estratos-mezcla` | `toolchain/tools/estratos-mezcla` | bmo-estratos | - |
| Toolchain | `bmo-estratos-put` | `toolchain/tools/estratos-put` | bmo-estratos | - |
| Toolchain | `bmo-firmar` | `toolchain/tools/bmo-firmar` | bmo-abi, bmo-cripto, bmo-firma, bmo-hash | bmo-abi |
| Toolchain | `bmo-fontgen` | `toolchain/tools/fontgen` | - | - |
| Toolchain | `bmo-fw-huella` | `toolchain/tools/fw-huella` | bmo-gpu-ga10x, bmo-hash | - |
| Toolchain | `bmo-hello-bex` | `toolchain/tools/hello-bex` | bmo-abi | bmo-abi |
| Toolchain | `bmo-huesped` | `toolchain/tools/espejo-cara/huesped` | - | - |
| Toolchain | `bmo-icono` | `toolchain/tools/bmo-icono` | bmo-imagen | - |
| Toolchain | `bmo-inti-hex` | `toolchain/tools/inti-hex` | bmo-inti-x86-64, bmo-mods | - |
| Toolchain | `bmo-maqueta` | `toolchain/tools/maqueta/cli` | bmo-imagen, bmo-maqueta-cascade, bmo-maqueta-compone, bmo-maqueta-diag, bmo-maqueta-emit, bmo-maqueta-layout, bmo-maqueta-node, bmo-maqueta-verdict | - |
| Toolchain | `bmo-maqueta-cascade` | `toolchain/tools/maqueta/cascade` | bmo-maqueta-diag, bmo-maqueta-dibujo, bmo-maqueta-node | - |
| Toolchain | `bmo-maqueta-compone` | `toolchain/tools/maqueta/compone` | bmo-imagen, bmo-maqueta-cascade, bmo-maqueta-diag, bmo-maqueta-dibujo, bmo-maqueta-layout, bmo-maqueta-node, bmo-maqueta-verdict | - |
| Toolchain | `bmo-maqueta-diag` | `toolchain/tools/maqueta/diag` | - | - |
| Toolchain | `bmo-maqueta-dibujo` | `toolchain/tools/maqueta/dibujo` | bmo-maqueta-diag | - |
| Toolchain | `bmo-maqueta-emit` | `toolchain/tools/maqueta/emit` | bmo-dibujo, bmo-letra, bmo-maqueta-cara, bmo-maqueta-cascade, bmo-maqueta-dibujo, bmo-maqueta-layout, bmo-maqueta-node, bmo-pinta | - |
| Toolchain | `bmo-maqueta-layout` | `toolchain/tools/maqueta/layout` | bmo-letra, bmo-maqueta-cascade, bmo-maqueta-diag, bmo-maqueta-dibujo, bmo-maqueta-node | - |
| Toolchain | `bmo-maqueta-lex` | `toolchain/tools/maqueta/lex` | - | - |
| Toolchain | `bmo-maqueta-node` | `toolchain/tools/maqueta/node` | bmo-maqueta-diag, bmo-maqueta-dibujo, bmo-maqueta-lex | - |
| Toolchain | `bmo-maqueta-verdict` | `toolchain/tools/maqueta/verdict` | bmo-maqueta-cascade, bmo-maqueta-diag, bmo-maqueta-dibujo, bmo-maqueta-layout | - |
| Toolchain | `bmo-metro` | `toolchain/tools/metro` | bmo-abi, bmo-ada-x86-64, bmo-c-x86-64, bmo-cobol-x86-64, bmo-cpp-x86-64, bmo-enlazar, bmo-inti-x86-64, bmo-lente-x86, bmo-lower, bmo-mods, bmo-titan-x86-64 | bmo-abi |
| Toolchain | `bmo-pack` | `toolchain/tools/bmo-pack` | bmo-abi, bmo-bsf | bmo-abi |
| Toolchain | `bmo-rpc-demo` | `toolchain/tools/rpc-demo` | bmo-abi | bmo-abi |
| Toolchain | `bmo-vista-ciudad` | `toolchain/tools/vista-ciudad` | bmo-ciudad | - |
