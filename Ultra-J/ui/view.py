"""Compile ULTRA-J markup and style sheets into two binary display lists."""
import argparse
from pathlib import Path
import struct
import xml.etree.ElementTree as ET

from compiler import publish
from runtime import read_bounded
from .style import PROPERTIES, require, stylesheet


TAGS = ('screen', 'panel', 'label', 'button')
ROOT = Path(__file__).resolve().parents[2]
GLYPHS = b'0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZ'
VIEW_BYTES = 3576
MAX_RECTS = (VIEW_BYTES - 12) // 6


def compile_view(markup, styles):
    return compile_view_rules(markup, stylesheet(styles))


def compile_view_rules(markup, rules):
    require('<!' not in markup and '<?' not in markup, 'El perfil admite etiquetas y texto ASCII')
    root = ET.fromstring(markup)
    require(root.tag == 'app' and not root.attrib and len(root) == 2
            and not (root.text or '').strip(), 'Se requiere app con dos pantallas')
    atlas = (ROOT / 'tools/desktop/cabina_font.bin').read_bytes()
    lists = []
    palette = {}
    for screen in root:
        require(screen.tag == 'screen', 'Se esperaba screen')
        rects = []

        def draw(x, y, w, h, color):
            require(0 <= x < x+w <= 640 and 0 <= y < y+h <= 400, 'Rectangulo fuera del lienzo')
            require(len(rects) < MAX_RECTS, 'Vista excede el presupuesto de rectangulos')
            require(color in palette or len(palette) < 64, 'Vista excede la paleta de 64 colores')
            index = palette.setdefault(color, len(palette))
            packed = x | y << 10 | w << 19 | h << 29 | index << 38
            rects.append(packed.to_bytes(6, 'little'))

        def node(element, origin, bounds, depth):
            require(depth <= 8 and element.tag in TAGS and (element.tag != 'screen' or depth == 0),
                    'Etiqueta invalida')
            require(set(element.attrib) == {'class'} and not (element.tail or '').strip(),
                    'Se requiere un atributo class y texto dentro de la etiqueta')
            style = rules.get(element.attrib['class'])
            require(style is not None and all(key in style for key in PROPERTIES[:4]),
                    f'Falta geometria para {element.attrib["class"]}')
            left, top, width, height = (style[k] for k in PROPERTIES[:4])
            require(0 <= left < left+width <= bounds[0] and 0 <= top < top+height <= bounds[1],
                    'Elemento fuera del padre')
            x, y = origin[0] + left, origin[1] + top
            if depth == 0:
                require((left, top, width, height) == (0, 0, 640, 400) and 'background' in style,
                        'La pantalla debe cubrir 640 por 400 pixeles')
            if 'background' in style:
                radius = style.get('border-radius', 0)
                require(radius <= min(16, width // 2, (height - 1) // 2) and (depth or radius == 0),
                        'Radio fuera de los limites del elemento')
                color = style['background']
                draw(x, y + radius, width, height - 2 * radius, color)
                for row in range(radius):
                    # Pixel centers inside the rounded corner.
                    inset = next(i for i in range(radius + 1)
                                 if (2*i + 1 - 2*radius)**2 + (2*row + 1 - 2*radius)**2 <= (2*radius)**2)
                    draw(x + inset, y + row, width - 2 * inset, 1, color)
                    draw(x + inset, y + height - row - 1, width - 2 * inset, 1, color)
            message = (element.text or '').strip()
            if element.tag in ('label', 'button'):
                require(message and not len(element) and 'color' in style, 'Texto, color y hoja requeridos')
                chars = message.encode('ascii')
                require(all(char in GLYPHS or char == 32 for char in chars),
                        'El atlas admite A-Z, 0-9 y espacios')
                scale = style.get('font-scale', 1)
                text_width = scale * sum(4 if char == 32 else atlas[GLYPHS.index(char) * 37] for char in chars)
                require(text_width <= width and height >= 12 * scale, 'Texto fuera de la etiqueta')
                cursor = (width - text_width) // 2 if style.get('text-align') == 'center' else 0
                text_y = y + (height - 12 * scale) // 2 if style.get('text-align') == 'center' else y
                for character in chars:
                    if character == 32:
                        cursor += 4 * scale
                        continue
                    index = GLYPHS.index(character) * 37
                    advance = atlas[index]
                    for row in range(12):
                        bits = int.from_bytes(atlas[index+1+3*row:index+4+3*row], 'little')
                        col = 0
                        while bits:
                            shade = bits & 3 != 0
                            length = 1
                            bits >>= 2
                            while bits and (bits & 3 != 0) == shade:
                                length += 1
                                bits >>= 2
                            if shade:
                                draw(x + cursor + col * scale, text_y + row * scale,
                                     length * scale, scale, style['color'])
                            col += length
                    cursor += advance * scale
            else:
                require(not message, 'El texto requiere una etiqueta label o button')
                for child in element:
                    node(child, (x, y), (width, height), depth + 1)

        node(screen, (0, 0), (640, 400), 0)
        lists.append(struct.pack('<H', len(rects)) + b''.join(rects))
    colors = b''.join(struct.pack('<I', color) for color in palette)
    binary = b'UJVI\x02\x02' + struct.pack('<H', len(palette)) + colors + b''.join(lists)
    require(len(binary) <= VIEW_BYTES, 'La vista excede su reserva de constantes')
    return binary


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('markup', type=Path)
    parser.add_argument('styles', type=Path)
    parser.add_argument('output', type=Path)
    args = parser.parse_args()
    try:
        markup = read_bounded(args.markup, 16384).decode('ascii')
        styles = read_bounded(args.styles, 16384).decode('ascii')
        data = compile_view(markup, styles)
        publish(args.output, data)
    except (ValueError, OSError, ET.ParseError) as error:
        parser.exit(1, f'{error}\n')


if __name__ == '__main__':
    main()
