"""Verify the Rust mixer preview and enumerate the QEMU HDA fixture."""
import argparse
import json
from pathlib import Path
import re
import struct
import subprocess
import wave


def check_wave(path):
    with wave.open(str(path), "rb") as wav:
        expected = (2, 2, 48000, 76800, "NONE")
        if wav.getparams()[:5] != expected:
            raise ValueError(f"Formato WAV inesperado: {wav.getparams()}")
        peaks = []
        for expected_peak in ((8000, 0), (0, 6000), (4000, 3000), (0, 0)):
            pcm = wav.readframes(19200)
            if len(pcm) != 19200 * 4:
                raise ValueError("Bloque WAV truncado")
            peak = [0, 0]
            for left, right in struct.iter_unpack("<hh", pcm):
                peak[0] = max(peak[0], abs(left))
                peak[1] = max(peak[1], abs(right))
            if tuple(peak) != expected_peak:
                raise ValueError(f"Picos WAV: {peak}, esperados {expected_peak}")
            peaks.append(peak)
    return dict(evidence="HOST", sample_rate=48000, frames=76800, stereo_peaks=peaks)


def check_hda(qemu):
    version = subprocess.check_output([str(qemu), "--version"], text=True).splitlines()[0]
    result = subprocess.run(
        [str(qemu), "-machine", "pc", "-accel", "tcg", "-S", "-nodefaults", "-display", "none",
         "-serial", "none", "-monitor", "stdio", "-audiodev", "none,id=out",
         "-device", "intel-hda", "-device", "hda-output,audiodev=out"],
        input="info pci\ninfo qtree\nquit\n", capture_output=True, text=True, check=True, timeout=15,
    )
    if not re.search(r"8086:2668", result.stdout, re.I) or not re.search(r"dev: hda-output", result.stdout):
        raise ValueError(f"QEMU no enumero la configuracion HDA: {result.stdout}")
    return dict(evidence="QEMU configuration", version=version, pci="8086:2668",
                codec="hda-output", guest_playback=False)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("wav", type=Path)
    parser.add_argument("--qemu", type=Path)
    args = parser.parse_args()
    result = {"wave": check_wave(args.wav)}
    if args.qemu:
        result["hda"] = check_hda(args.qemu)
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
