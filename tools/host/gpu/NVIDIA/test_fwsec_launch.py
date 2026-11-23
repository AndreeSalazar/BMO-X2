"""Exercise the Falcon loader with synthetic BAR0 registers on Windows HOST."""

from concurrent.futures import ThreadPoolExecutor
import ctypes
import os
from pathlib import Path
import struct
import subprocess
import tempfile
import unittest

from .sec2_booter import prepare_sec2_booter
from .test_sec2_booter import booter


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
        domain = directory / "domain.obj"
        subprocess.run([LLVM / "clang.exe", "--target=x86_64-pc-windows-msvc", "-c",
                        ROOT / "kernel/drivers/bus/amdvi/fwsec_domain.S", "-o", domain], check=True)
        ivrs = directory / "ivrs.obj"
        subprocess.run([LLVM / "clang.exe", "--target=x86_64-pc-windows-msvc", "-c",
                        ROOT / "kernel/drivers/bus/amdvi/board_ivrs.S", "-o", ivrs], check=True)
        sec2 = directory / "sec2.obj"
        subprocess.run([LLVM / "clang.exe", "--target=x86_64-pc-windows-msvc", "-c",
                        ROOT / "kernel/drivers/GPU/NVIDIA/sec2_prepare.S", "-o", sec2], check=True)
        subprocess.run([LLVM / "lld-link.exe", "/dll", "/noentry", "/nodefaultlib",
                        "/export:nvidia_launch_ga106_fwsec", "/export:nvidia_prepare_ga106_falcon",
                        "/export:amdvi_stage_fwsec_domain", "/export:amdvi_matches_board_ivrs",
                        "/export:nvidia_prepare_sec2_image", f"/out:{dll}", obj, domain, ivrs, sec2], check=True)
        cls.library = ctypes.WinDLL(str(dll))
        cls.addClassCleanup(FreeLibrary, cls.library._handle)
        cls.launch = cls.library.nvidia_launch_ga106_fwsec
        cls.launch.argtypes = [ctypes.c_void_p, ctypes.c_uint64, ctypes.c_uint64, ctypes.c_void_p]
        cls.launch.restype = ctypes.c_int
        cls.prepare = cls.library.nvidia_prepare_ga106_falcon
        cls.prepare.argtypes = [ctypes.c_void_p, ctypes.c_uint64]
        cls.prepare.restype = ctypes.c_int
        cls.domain = cls.library.amdvi_stage_fwsec_domain
        cls.domain.argtypes = [ctypes.c_void_p, ctypes.c_uint64, ctypes.c_uint64]
        cls.domain.restype = ctypes.c_int
        cls.ivrs_match = cls.library.amdvi_matches_board_ivrs
        cls.ivrs_match.argtypes = [ctypes.c_void_p, ctypes.c_uint32]
        cls.ivrs_match.restype = ctypes.c_int
        cls.prepare_sec2 = cls.library.nvidia_prepare_sec2_image
        cls.prepare_sec2.argtypes = [ctypes.c_void_p, ctypes.c_void_p, ctypes.c_uint32]
        cls.prepare_sec2.restype = ctypes.c_int

    def test_native_sec2_workspace_matches_host_encoder(self):
        image = bytes(booter(native_geometry=True))
        pages = 15 * 4096
        workspace = (ctypes.c_uint8 * (pages + 8192))()
        address = (ctypes.addressof(workspace) + 4096) & -4096
        ctypes.memset(address + pages, 0x5a, 4096)
        for fuse in (0, 1, 0x10000):
            with self.subTest(fuse=fuse):
                expected, report = prepare_sec2_booter(image, fuse)
                ctypes.memset(address, 0xa5, pages)
                self.assertEqual(self.prepare_sec2(image, address, fuse), report['signature_index']+1)
                self.assertEqual(ctypes.string_at(address, pages), expected)
        self.assertEqual(ctypes.string_at(address + pages, 4096), bytes([0x5a])*4096)
        for fuse in (2, 0xffffffff, 0xbadf5620):
            with self.subTest(fuse=fuse):
                self.assertEqual(self.prepare_sec2(image, address, fuse), 0)
                self.assertEqual(ctypes.string_at(address, pages), expected)

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
        self.assertEqual(self.read(FALCON + 0x14), 0xFFFFFFFF)
        self.write(FALCON + 0xF4, 0x80001000)
        self.assertEqual(self.prepare(self.mapping, 1_000_000), 2)
        self.assertEqual(self.read(FALCON + 0x84), 0)
        self.assertEqual(self.read(DMA_COMMAND), 0)

    def test_reset_ready_is_advisory_and_launch_requires_completed_scrub(self):
        self.write(0x111388, 0x110)  # Halted, inactive, unrelated bit set.
        self.write(FALCON + 0xF4, 0)
        self.assertEqual(self.prepare(self.mapping, 1_000_000), 1)
        self.write(FALCON + 0xF4, 0x1000)
        self.assertEqual(self.launch(self.mapping, 1_000_000, FWSEC_IOVA, self.result), 0)
        self.assertEqual(list(self.result), [0] * 7)
        self.write(FALCON + 0xF4, 0)
        self.assertEqual(self.replay(FALCON + 0x100, 0x02FFEE00), 1)

    def test_selects_falcon_after_reset_even_if_riscv_halted_bit_clears(self):
        bcr = FALCON + 0x1668
        irq_ack = FALCON + 0x14
        self.write(bcr, 0x110)
        with ThreadPoolExecutor(max_workers=1) as worker:
            run = worker.submit(self.prepare, self.mapping, 90_000_000)
            while self.read(irq_ack) == 0 and not run.done():
                pass
            self.assertEqual(self.read(bcr), 0x110)
            self.write(0x111388, 0)
            while self.read(bcr) != 0 and not run.done():
                pass
            self.assertFalse(run.done(), "Falcon core selection was never requested")
            self.assertEqual(self.read(FALCON + 0x3C0) & 1, 0)
            self.write(bcr, 1)
            self.assertEqual(run.result(), 1)
        self.assertEqual(self.replay(FALCON + 0x100, 0x02FFEE00), 1)

    def domain_memory(self):
        kernel = ctypes.WinDLL("kernel32", use_last_error=True)
        alloc, free = kernel.VirtualAlloc, kernel.VirtualFree
        alloc.argtypes = [ctypes.c_void_p, ctypes.c_size_t, ctypes.c_uint32, ctypes.c_uint32]
        alloc.restype = ctypes.c_void_p
        free.argtypes = [ctypes.c_void_p, ctypes.c_size_t, ctypes.c_uint32]
        free.restype = ctypes.c_int
        capacity = 0x209000
        for candidate in range(0x02000000, 0x10000000 - capacity, 0x400000):
            base = alloc(candidate, capacity, 0x3000, 4)
            if base:
                break
        else:
            self.fail("could not reserve the low identity-map test window")
        self.addCleanup(lambda: free(base, 0, 0x8000))
        memory = (ctypes.c_uint8 * capacity).from_address(base)
        return base, memory

    def test_domain_exposes_exactly_fifteen_read_only_pages(self):
        base, memory = self.domain_memory()
        payload = base - 0xf000
        graphics = 0x2900 * 32
        ctypes.memset(base + 0x207000, 0xff, 8192)
        struct.pack_into("<Q", memory, graphics + 32, 0xabcdef)  # Audio untouched.
        self.assertEqual(self.domain(base, payload, payload), 2)
        read = 1 << 61
        self.assertEqual(struct.unpack_from("<5Q", memory, graphics),
                         (base + 0x207000 | read | 0x403, 5, 0, 0, 0xabcdef))
        root = [0] * 512
        leaf = [0] * 512
        root[FWSEC_IOVA >> 21] = base + 0x208000 | read | 0x201
        for index in range(15):
            leaf[((FWSEC_IOVA >> 12) & 511) + index] = payload + index * 4096 | read | 1
        self.assertEqual(struct.unpack_from("<1024Q", memory, 0x207000), tuple(root + leaf))

    def test_domain_stays_denied_for_absent_or_out_of_range_fwsec(self):
        base, memory = self.domain_memory()
        graphics = 0x2900 * 32
        for address in (0, base - 0xe000, base - 0xf001, base - 0x11000):
            with self.subTest(address=address):
                struct.pack_into("<4Q", memory, graphics, 0x100043, 5, 1, 1)
                self.assertEqual(self.domain(base, address, base - 0x10000), 1)
                self.assertEqual(struct.unpack_from("<4Q", memory, graphics),
                                 (base + 0x200000 | (3 << 61) | 0x403, 0, 0, 0))
                self.assertFalse(any(memory[0x207000:]))
        self.assertEqual(self.domain(base + 1, 0, base), 0)

    def test_board_ivrs_requires_exact_routing(self):
        from ..ivrs import inspect, windows_ivrs

        self.assertEqual(self.ivrs_match(None, 208), 0)
        self.assertEqual(self.ivrs_match(bytes(208), 208), 0)
        try:
            original = windows_ivrs()
        except OSError as error:
            self.skipTest(str(error))
        report = inspect(original, [(0, 0xa0), (0, 0xa3)])
        if report['table_sha256'] != 'd2b4e55ee37be93d6e764136059f140e847368118d447c345964ef21471202ec':
            self.assertEqual(self.ivrs_match(original, len(original)), 0)
            return
        self.assertEqual(self.ivrs_match(original, len(original)), 1)
        self.assertEqual(self.ivrs_match(original, len(original) - 1), 0)
        relabeled = bytearray(original)
        relabeled[10] ^= 1
        relabeled[9] = (relabeled[9] - sum(relabeled)) & 0xff
        self.assertEqual(self.ivrs_match(bytes(relabeled), len(relabeled)), 1)
        relabeled[8] = 1
        self.assertEqual(self.ivrs_match(bytes(relabeled), len(relabeled)), 0)
        altered = bytearray(original)
        altered[-1] ^= 1
        self.assertEqual(self.ivrs_match(bytes(altered), len(altered)), 0)

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
        for offset, value in ((FALCON + 0x1668, 0x10), (0x111388, 0x90)):
            with self.subTest(offset=offset):
                original = self.read(offset)
                self.write(offset, value)
                before = bytes(self.bar)
                self.assertEqual(self.launch(self.mapping, 25_000_000, FWSEC_IOVA, self.result), 0)
                self.assertEqual(self.bar, before)
                self.write(offset, original)

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
