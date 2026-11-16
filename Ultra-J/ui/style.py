"""Bounded UJC style profile; not a complete CSS implementation."""
import re

PROPERTIES = ('left', 'top', 'width', 'height', 'background', 'color', 'border-radius', 'font-scale',
              'text-align')


def require(condition, message):
    if not condition:
        raise ValueError(message)


def stylesheet(source):
    rules = {}
    while source.strip():
        match = re.match(r'\s*([a-z][a-z0-9-]*)\s*\{([^{}]*)\}', source)
        require(match is not None, 'Regla de estilo invalida')
        key, declarations = match.groups()
        require(key not in rules, f'Regla repetida {key}')
        rules[key] = rule = {}
        for declaration in declarations.split(';'):
            if not declaration.strip():
                continue
            name, _, value = (part.strip() for part in declaration.partition(':'))
            require(name in PROPERTIES and name not in rule, f'Propiedad invalida {name}')
            color = name in ('color', 'background')
            if name == 'text-align':
                require(value in ('left', 'center'), f'Valor invalido para {name}')
                rule[name] = value
                continue
            pattern = r'#[0-9a-fA-F]{6}' if color else r'[1-3]' if name == 'font-scale' else r'[0-9]{1,3}px'
            require(re.fullmatch(pattern, value), f'Valor invalido para {name}')
            rule[name] = int(value[1:], 16) if color else int(value.removesuffix('px'))
        source = source[match.end():]
    return rules


