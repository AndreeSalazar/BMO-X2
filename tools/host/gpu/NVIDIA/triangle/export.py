"""Check raw Vulkan frames and turn them into a looping preview."""

import argparse
import hashlib
import json
from pathlib import Path
from time import perf_counter

from PIL import Image, ImageChops


WIDTH, HEIGHT = 480, 360
FRAME_COUNT = 48


def compare_cpu_frame_zero(raw):
    # At angle zero, clip W is one and the vertex colors interpolate linearly.
    vertices = [(WIDTH * (x * 0.75 + 1) / 2, HEIGHT * (y + 1) / 2)
                for x, y in ((0, -0.78), (0.70, 0.42), (-0.70, 0.42))]
    palette = ((0.97, 0.65, 1.00), (0.25, 0.95, 0.83), (0.29, 0.55, 1.00))
    (ax, ay), (bx, by), (cx, cy) = vertices
    denominator = (by - cy) * (ax - cx) + (cx - bx) * (ay - cy)
    background = bytes((8, 9, 18, 255))
    edge = bytes(4)
    channels = tuple(zip(*palette))
    checked = interior = max_error = 0
    start = perf_counter()
    reference = bytearray()
    for y in range(HEIGHT):
        for x in range(WIDTH):
            dx, dy = x + 0.5 - cx, y + 0.5 - cy
            a = ((by - cy) * dx + (cx - bx) * dy) / denominator
            b = ((cy - ay) * dx + (ax - cx) * dy) / denominator
            c = 1 - a - b
            distance = min(a, b, c)
            # Skip the immediate raster edge, where vertex quantization can change coverage.
            if abs(distance) < 0.002:
                reference.extend(edge)
            elif distance < 0:
                reference.extend(background)
            else:
                reference.extend(round(255 * (a * r + b * s + c * t)) for r, s, t in channels)
                reference.append(255)
    cpu_ms = (perf_counter() - start) * 1000
    for offset in range(0, len(reference), 4):
        expected = reference[offset:offset + 4]
        if expected[3] == 0:
            continue
        checked += 1
        interior += expected != background
        max_error = max(max_error, *(abs(a - b) for a, b in zip(expected, raw[offset:offset + 4])))
    if not interior or max_error > 1:
        raise ValueError(f'Frame zero differs from CPU reference by {max_error} RGBA8 levels')
    return dict(compared_pixels=checked, interior_pixels=interior,
                edge_pixels_skipped=WIDTH * HEIGHT - checked, max_channel_error=max_error,
                python_raster_ms=round(cpu_ms, 3))


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
        if index == 0:
            cpu_reference = compare_cpu_frame_zero(raw)
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
        'cpu_reference_frame_zero': cpu_reference,
        'rgba8_sequence_sha256': hashlib.sha256(''.join(hashes).encode('ascii')).hexdigest(),
        'gif_sha256': hashlib.sha256(gif.read_bytes()).hexdigest(),
        'png_sha256': hashlib.sha256(png.read_bytes()).hexdigest(),
    }


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('directory', type=Path)
    print(json.dumps(export(parser.parse_args().directory), indent=2))
