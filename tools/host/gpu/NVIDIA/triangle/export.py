"""Check raw Vulkan frames and turn them into a looping preview."""

import argparse
import hashlib
import json
from pathlib import Path

from PIL import Image, ImageChops


WIDTH, HEIGHT = 480, 360
FRAME_COUNT = 48


def export(directory):
    frames = []
    hashes = []
    areas = []
    for index in range(FRAME_COUNT):
        raw = (directory/'frames'/f'{index:02d}.rgba').read_bytes()
        if len(raw) != WIDTH*HEIGHT*4:
            raise ValueError(f'Frame {index}: incorrect RGBA8 length')
        if raw[:4] != bytes((8, 9, 18, 255)) or set(raw[3::4]) != {255}:
            raise ValueError(f'Frame {index}: incorrect clear color or alpha')
        hashes.append(hashlib.sha256(raw).hexdigest())
        frame = Image.frombytes('RGBA', (WIDTH, HEIGHT), raw).convert('RGB')
        clear = Image.new('RGB', frame.size, frame.getpixel((0, 0)))
        changed_rgb = ImageChops.difference(frame, clear).split()
        changed = ImageChops.lighter(ImageChops.lighter(*changed_rgb[:2]), changed_rgb[2])
        areas.append(WIDTH*HEIGHT-changed.histogram()[0])
        frames.append(frame)

    if len(set(hashes)) != FRAME_COUNT or min(areas) <= 0 or max(areas) < 2*min(areas):
        raise ValueError('Expected a rotating triangle with changing projected area')
    png = directory/'triangulo-rtx3060.png'
    gif = directory/'triangulo-rtx3060.gif'
    frames[0].save(png)
    frames[0].save(gif, save_all=True, append_images=frames[1:], duration=50, loop=0)
    with Image.open(gif) as preview:
        if preview.n_frames != FRAME_COUNT:
            raise ValueError('Incorrect GIF frame count')

    return {
        'width': WIDTH,
        'height': HEIGHT,
        'unique_rgba8_frames': len(set(hashes)),
        'colored_pixels_per_frame': {'min': min(areas), 'max': max(areas)},
        'rgba8_sequence_sha256': hashlib.sha256(''.join(hashes).encode('ascii')).hexdigest(),
        'gif_sha256': hashlib.sha256(gif.read_bytes()).hexdigest(),
        'png_sha256': hashlib.sha256(png.read_bytes()).hexdigest(),
    }


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('directory', type=Path)
    print(json.dumps(export(parser.parse_args().directory), indent=2))
