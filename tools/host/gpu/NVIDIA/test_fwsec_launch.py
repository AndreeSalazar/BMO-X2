"""Exercise the Falcon loader with synthetic BAR0 registers on Windows HOST."""

from concurrent.futures import ThreadPoolExecutor
import ctypes
import os
from pathlib import Path
import struct
import subprocess
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[4]
LLVM = Path(os.environ.get("ProgramFiles", "C:/Program Files")) / "LLVM/bin"
FALCON = 0x110000
DMA_COMMAND = FALCON + 0x118
FWSEC_IOVA = 0x0A107000
IMEM = 57856
DMEM = 2048


@unittest.skipUnless(os.name == "nt", "requires Windows and LLVM")
class FwsecLaunch(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        from _ctypes import FreeLibrary

        folder = tempfile.TemporaryDirectory(prefix="bmo-fwsec-launch-")
        cls.addClassCleanup(folder.cleanup)
        directory = Path(folder.name)
        source = ROOT / "kernel/drivers/GPU/NVIDIA/fwsec_launch.S"
        obj, dll = directory / "launch.obj", directory / "launch.dll"
        subprocess.run([LLVM / "clang.exe", "--target=x86_64-pc-windows-msvc",
                        "-c", source, "-o", obj], check=True)
        subprocess.run([LLVM / "lld-link.exe", "/dll", "/noentry", "/nodefaultlib",
                        "/export:nvidia_launch_ga106_fwsec", "/export:nvidia_prepare_ga106_falcon",
                        f"/out:{dll}", obj], check=True)
        cls.library = ctypes.WinDLL(str(dll))
        cls.addClassCleanup(FreeLibrary, cls.library._handle)
        cls.launch = cls.library.nvidia_launch_ga106_fwsec
        cls.launch.argtypes = [ctypes.c_void_p, ctypes.c_uint64, ctypes.c_uint64, ctypes.c_void_p]
        cls.launch.restype = ctypes.c_int
        cls.prepare = cls.library.nvidia_prepare_ga106_falcon
        cls.prepare.argtypes = [ctypes.c_void_p, ctypes.c_uint64]
        cls.prepare.restype = ctypes.c_int

    def setUp(self):
        self.bar = bytearray(0x200000)
        self.mapping = (ctypes.c_char * len(self.bar)).from_buffer(self.bar)
        self.result = (ctypes.c_uint32 * 7)()
        self.write(0, 0xB76000A1)
        self.write(0x111388, 0x10)
        self.write(FALCON + 0xF4, 0x80000000)
        self.write(FALCON + 0x108, (DMEM << 1) | (IMEM >> 8))

    def read(self, offset):
        return struct.unpack_from("<I", self.bar, offset)[0]

    def write(self, offset, value):
        struct.pack_into("<I", self.bar, offset, value)

    def test_prepares_cold_falcon_without_starting_or_issuing_dma(self):
        self.write(FALCON + 0x3C0, 0xA0)
        self.write(FALCON + 0x48, 0xF)
        self.assertEqual(self.prepare(self.mapping, 25_000_000), 1)
        self.assertEqual(self.read(FALCON + 0x3C0), 0xA0)
        self.assertEqual(self.read(FALCON + 0x48), 0xC)
        self.assertEqual(self.read(FALCON + 0x14), 0xFFFFFFFF)
        self.assertEqual(self.read(FALCON + 0x84), 0xB76000A1)
        self.assertEqual(self.read(FALCON + 0x100), 0)
        self.assertEqual(self.read(DMA_COMMAND), 0)

    def test_prepare_rejects_active_riscv_or_reset_before_writes(self):
        for offset, value in ((0x111388, 0x80), (FALCON + 0x3C0, 1)):
            with self.subTest(offset=offset):
                original = self.read(offset)
                self.write(offset, value)
                before = bytes(self.bar)
                self.assertEqual(self.prepare(self.mapping, 25_000_000), 0)
                self.assertEqual(self.bar, before)
                self.write(offset, original)

    def test_prepare_reports_selector_or_scrub_timeout(self):
        self.write(FALCON + 0x1668, 0x10)
        self.assertEqual(self.prepare(self.mapping, 1_000_000), 2)
        self.assertEqual(self.read(FALCON + 0x14), 0)
        self.write(FALCON + 0xF4, 0x80001000)
        self.assertEqual(self.prepare(self.mapping, 1_000_000), 2)
        self.assertEqual(self.read(FALCON + 0x84), 0)
        self.assertEqual(self.read(DMA_COMMAND), 0)

    def test_rejects_wrong_dma_window_and_active_wpr_before_writes(self):
        before = bytes(self.bar)
        self.assertEqual(self.launch(self.mapping, 25_000_000, FWSEC_IOVA + 4096, self.result), 0)
        self.assertEqual(self.bar, before)
        self.write(0x1FA828, 0x02FFEE00)
        before = bytes(self.bar)
        self.assertEqual(self.launch(self.mapping, 25_000_000, FWSEC_IOVA, self.result), 0)
        self.assertEqual(self.bar, before)
        self.assertEqual(list(self.result), [0] * 7)

    def test_leaves_the_riscv_core_alone(self):
        self.write(FALCON + 0x1668, 0x10)
        before = bytes(self.bar)
        self.assertEqual(self.launch(self.mapping, 25_000_000, FWSEC_IOVA, self.result), 0)
        self.assertEqual(self.bar, before)

    def test_dma_failure_never_starts_falcon(self):
        for status in (0xBADF5620, 1):
            with self.subTest(status=status):
                self.result[0] = 0
                self.write(DMA_COMMAND, status)
                self.assertEqual(self.launch(self.mapping, 1_000_000, FWSEC_IOVA, self.result), 2)
                self.assertEqual(list(self.result), [1, 0, 0, 0, 0, 0, 0])
                self.assertEqual(self.read(FALCON + 0x100), 0)
                self.assertEqual(self.read(FALCON + 0x110), 0)

    def replay(self, start, wpr_high, scratch=0):
        with ThreadPoolExecutor(max_workers=1) as worker:
            run = worker.submit(self.launch, self.mapping, 25_000_000, FWSEC_IOVA, self.result)
            for offset in range(0, IMEM + DMEM, 256):
                command = 0x614 if offset < IMEM else 0x604
                while self.read(DMA_COMMAND) != command and not run.done():
                    pass
                self.assertFalse(run.done(), f"Falcon DMA stopped at offset {offset}")
                source_base = FWSEC_IOVA if offset < IMEM else FWSEC_IOVA + IMEM
                local_offset = offset if offset < IMEM else offset - IMEM
                self.assertEqual(self.read(FALCON + 0x110), source_base >> 8)
                self.assertEqual(self.read(FALCON + 0x128), 0)
                self.assertEqual(self.read(FALCON + 0x114), local_offset)
                self.assertEqual(self.read(FALCON + 0x11C), local_offset)
                self.write(DMA_COMMAND, command | 2)

            while self.read(start) != 2 and not run.done():
                pass
            self.assertFalse(run.done(), "FWSEC was never started")
            self.assertEqual(self.read(FALCON + 0x1210), 1444)
            self.assertEqual(self.read(FALCON + 0x119C), 0x400)
            self.assertEqual(self.read(FALCON + 0x1198), 9)
            self.assertEqual(self.read(FALCON + 0x1180), 1)
            self.write(0x1438, scratch)
            self.write(0x1FA824, 0x02FFE000)
            self.write(0x1FA828, wpr_high)
            self.write(FALCON + 0x100, 0x10)
            return run.result()

    def test_signed_fwsec_launch_accepts_only_the_measured_wpr2(self):
        self.assertEqual(self.replay(FALCON + 0x100, 0x02FFEE00), 1)
        self.assertEqual(list(self.result), [4, IMEM + DMEM, 0, 0, 0, 0x02FFE000, 0x02FFEE00])
        self.assertEqual(self.launch(self.mapping, 25_000_000, FWSEC_IOVA, self.result), 0)

    def test_cpu_start_alias_and_firmware_error(self):
        self.write(FALCON + 0x100, 0x40)
        self.assertEqual(self.replay(FALCON + 0x130, 0x02FFEE00, scratch=0x150000), 3)
        self.assertEqual(list(self.result), [3, IMEM + DMEM, 0, 0, 0x150000, 0x02FFE000, 0x02FFEE00])

    def test_halted_falcon_with_different_wpr_is_a_failure(self):
        self.assertEqual(self.replay(FALCON + 0x100, 0x02FFFF00), 3)
        self.assertEqual(self.result[0], 3)


if __name__ == "__main__":
    unittest.main()
