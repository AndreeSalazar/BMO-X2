"""Compatibility entry point for the HOST SBEF CLI."""
from host.cli import MAX_ELF, MAX_IMAGE, Rejection, inspect, main, pack_elf, probe_pe, run


if __name__ == '__main__':
    raise SystemExit(main())
