"""HOST-only Driver.register profile: validate requests, never grant resources."""
import hashlib
import json
from pathlib import Path, PurePosixPath
import re

from compiler import MAX_SOURCE, publish
from package import PackageError, graph_report, load
from host.diagnostics import Rejection
from host.sbef.format import MAX_IMAGE, inspect

TOKEN = re.compile(r'\s+|//[^\n]*|"[^"\\\r\n]*"|[A-Za-z_][A-Za-z_0-9]*|[0-9]{1,10}|[{}().,;]')
NAME = re.compile(r'[a-z][a-z0-9_]{0,47}')


def fail(code, path, message, source='', offset=0, **details):
    raise PackageError(code, path, message, Line=source.count('\n', 0, offset) + 1,
                       Column=offset - source.rfind('\n', 0, offset), **details)


def declaration(path, root):
    raw = load(path, root, MAX_SOURCE)
    try:
        source = raw.decode('ascii')
    except UnicodeDecodeError as error:
        fail('DRIVER_TEXT', path, 'La declaracion requiere ASCII.', raw.decode('ascii', errors='replace'), error.start)
    tokens = []
    cursor = 0
    while cursor < len(source):
        match = TOKEN.match(source, cursor)
        if not match:
            fail('DRIVER_SYNTAX', path, 'Token no admitido.', source, cursor)
        word = match[0]
        if not word.isspace() and not word.startswith('//'):
            tokens.append((word, cursor))
        cursor = match.end()
    index = 0

    def take(expected=None):
        nonlocal index
        word, offset = tokens[index] if index < len(tokens) else ('', len(source))
        if not word or expected is not None and word != expected:
            fail('DRIVER_SYNTAX', path, f'Se esperaba {expected or "un token"}.', source, offset)
        index += 1
        return word, offset

    take('class')
    name, offset = take()
    if not re.fullmatch('[A-Za-z_][A-Za-z_0-9]{0,63}', name):
        fail('DRIVER_CLASS', path, 'Nombre de clase invalido.', source, offset)
    for word in ('{', 'void', 'register', '(', ')', '{'):
        take(word)
    calls = []
    while index < len(tokens) and tokens[index][0] not in ('}', 'return'):
        take('Driver')
        take('.')
        method, offset = take()
        take('(')
        args = []
        while index < len(tokens) and tokens[index][0] != ')':
            word, argument_offset = take()
            if word.startswith('"'):
                args.append(word[1:-1])
            elif re.fullmatch('[0-9]{1,10}', word):
                args.append(int(word))
            else:
                fail('DRIVER_ARGUMENT', path, 'Solo literales de texto o enteros.', source, argument_offset)
            if index < len(tokens) and tokens[index][0] == ')':
                break
            take(',')
            if index < len(tokens) and tokens[index][0] == ')':
                fail('DRIVER_ARGUMENT', path, 'Falta un argumento tras la coma.', source, tokens[index][1])
        take(')')
        take(';')
        calls.append((method, args, offset))
        if len(calls) > 64:
            fail('DRIVER_LIMIT', path, 'Demasiadas declaraciones.', source, offset)
    if index < len(tokens) and tokens[index][0] == 'return':
        take('return')
        take(';')
    take('}')
    take('}')
    if index != len(tokens):
        fail('DRIVER_SYNTAX', path, 'Contenido tras el cierre de clase.', source, tokens[index][1])
    return source, raw, name, calls


def pci_id(value):
    return isinstance(value, str) and re.fullmatch('[0-9a-fA-F]{4}:[0-9a-fA-F]{4}', value) and 0 < int(value[:4], 16) < 0xffff


def request(path, root, graph):
    source, raw, name, calls = declaration(path, root)
    values, dependencies = {}, []
    signatures = dict(target=(str,), pci=(str,), backend=(str,), memory=(int,),
                      mmio=(int, int, int), dma=(int,), events=(), depends=(str,))
    for method, args, offset in calls:
        signature = signatures.get(method)
        if signature is None or len(args) != len(signature) or any(type(a) is not t for a, t in zip(args, signature)):
            fail('DRIVER_CALL', path, 'Operacion o firma no admitida.', source, offset, Method=method)
        if method == 'depends':
            if not NAME.fullmatch(args[0]) or args[0] in dependencies:
                fail('DRIVER_DEPENDENCY', path, 'Dependencia invalida o repetida.', source, offset)
            dependencies.append(args[0])
        elif method in values:
            fail('DRIVER_DUPLICATE', path, 'Declaracion repetida.', source, offset, Method=method)
        else:
            values[method] = args
    for method in ('target', 'pci', 'backend', 'memory'):
        if method not in values:
            fail('DRIVER_REQUIRED', path, 'Falta declaracion obligatoria.', source, Method=method)
    if values['target'] != ['x86-64'] or not pci_id(values['pci'][0]):
        fail('DRIVER_TARGET', path, 'Se requiere x86-64 e identidad PCI concreta.', source)
    backend = PurePosixPath(values['backend'][0])
    if (not backend.parts or backend.is_absolute() or backend.suffix != '.sbef'
            or any(not re.fullmatch('[A-Za-z0-9_-][A-Za-z0-9_.-]*', p) for p in backend.parts)):
        fail('DRIVER_BACKEND_PATH', path, 'Backend local .sbef sin escapes de carpeta.', source)
    memory = values['memory'][0]
    if not 8192 <= memory <= 64 * 1024 * 1024 or memory % 4096:
        fail('DRIVER_MEMORY', path, 'Limite RAM de 8 KiB a 64 MiB en paginas de 4 KiB.', source)
    resources = []
    if 'mmio' in values:
        bar, offset, size = values['mmio']
        if not 0 <= bar <= 5 or offset % 4096 or size % 4096 or not 4096 <= size <= 1024 * 1024 or offset + size > 16 * 1024 * 1024:
            fail('DRIVER_MMIO', path, 'BAR o ventana MMIO fuera del perfil.', source)
        resources.append(dict(Kind='mmio', Bar=bar, Offset=offset, Bytes=size))
    if 'dma' in values:
        size = values['dma'][0]
        if not 4096 <= size <= 16 * 1024 * 1024 or size % 4096:
            fail('DRIVER_DMA', path, 'Reserva DMA invalida.', source)
        resources.append(dict(Kind='dma', Bytes=size, RequiresIommu=True))
    if 'events' in values:
        resources.append(dict(Kind='events'))
    backend_path = path.parent.joinpath(*backend.parts)
    graph.append(dict(From=path.relative_to(root).as_posix(),
                      To=backend_path.relative_to(root).as_posix(), Reason='native backend'))
    image = load(backend_path, root, MAX_IMAGE)
    try:
        native = inspect(image)
    except Rejection as error:
        raise PackageError('DRIVER_BACKEND', backend_path, 'SBEF rechazado.', Native=error.report()) from error
    if native['AbiVersion'] != 1:
        raise PackageError('DRIVER_ABI', backend_path, 'El perfil requiere ABI 1.')
    mapped = sum(region['MappedBytes'] for region in native['Regions'])
    if mapped + 4096 > memory:
        raise PackageError('DRIVER_MEMORY', path, 'El limite no cubre regiones y pila de 4 KiB.', StaticBytes=mapped + 4096)
    return dict(Name=name, Source=path.relative_to(root).as_posix(), SourceSHA256=hashlib.sha256(raw).hexdigest(),
                Pci=values['pci'][0].upper(), Target='x86-64', Abi=1,
                Backend=backend_path.relative_to(root).as_posix(), BackendSHA256=hashlib.sha256(image).hexdigest(),
                StaticMappedBytes=mapped, StackBudgetBytes=4096, MemoryLimitBytes=memory,
                RequestedResources=resources, Dependencies=dependencies)


def check_driver(root):
    root = root.resolve()
    graph, active, modules = [dict(From='.', To='main.uj', Reason='driver declaration')], [], {}

    def visit(path):
        relative = path.relative_to(root).as_posix()
        if relative in active:
            raise PackageError('DRIVER_CYCLE', path, 'Ciclo de dependencias de driver.', Chain=active + [relative])
        if relative in modules:
            return
        if len(active) >= 16 or len(modules) + len(active) >= 32:
            raise PackageError('DRIVER_LIMIT', path, 'Limite de dependencias de driver.')
        active.append(relative)
        module = request(path, root, graph)
        for name in module['Dependencies']:
            child = root / 'dependencies' / name / 'main.uj'
            graph.append(dict(From=relative, To=child.relative_to(root).as_posix(), Reason='driver dependency'))
            try:
                visit(child)
            except PackageError as error:
                error.report.setdefault('RequiredBy', str(path))
                raise
        active.pop()
        modules[relative] = module

    try:
        visit(root / 'main.uj')
    except PackageError as error:
        graph_report(root, graph, error.report)
        raise
    graph_report(root, graph)
    return dict(Schema=1, Kind='ULTRA-J_DRIVER_REQUEST', Evidence='HOST', HostValidated=True,
                RuntimeReady=False, GrantedCapabilities=[],
                Pending=['kernel_resource_grants', 'isolated_driver_process', 'transport_events'],
                Modules=list(modules.values()), StartOrder=list(modules), Dependencies=graph)


def prepare_driver(root):
    root = root.resolve()
    report = check_driver(root)
    output = root / 'build'
    if output.resolve() != output:
        raise PackageError('DRIVER_OUTPUT', output, 'La salida debe permanecer dentro del paquete.')
    output.mkdir(exist_ok=True)
    publish(output / 'driver-request.json', (json.dumps(report, indent=2) + '\n').encode('ascii'))
    return report


def new_driver(name, pci):
    if not NAME.fullmatch(name) or not pci_id(pci):
        raise PackageError('DRIVER_NEW', name, 'Nombre simple y --pci VVVV:DDDD obligatorios.')
    root = Path.cwd() / name
    root.mkdir()
    classname = ''.join(part.capitalize() for part in name.split('_'))
    source = f'''class {classname} {{
    void register() {{
        Driver.target("x86-64");
        Driver.pci("{pci.upper()}");
        Driver.backend("backend.sbef");
        Driver.memory(65536);
        Driver.mmio(0, 0, 65536);
        Driver.dma(40960);
        Driver.events();
    }}
}}
'''
    publish(root / 'main.uj', source.encode('ascii'))
    return root
