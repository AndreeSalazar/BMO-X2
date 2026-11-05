"""Only fresh CASM run directories inside this project may contain VM outputs."""
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def workspace(path):
    path = Path(path).resolve()
    if not path.is_relative_to((ROOT/'build/CASM').resolve()) or not path.name.startswith('run-') or not path.is_dir():
        raise ValueError('QEMU-WORKSPACE: se requiere un run dentro de build/CASM')
    if ',' in str(path):
        raise ValueError('QEMU-WORKSPACE: la ruta no puede contener comas')
    return path
