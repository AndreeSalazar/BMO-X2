import struct
import unittest

from .sec2_booter import prepare_sec2_booter, sec2_booter_layout


def booter(*, native_geometry=False):
    image_offset = 888
    imem_bytes, dmem_bytes = (35584, 25088) if native_geometry else (512, 768)
    dmem_offset = 256 + imem_bytes
    image_bytes = dmem_offset + dmem_bytes
    container = bytearray(image_offset + image_bytes)
    container[60:444] = bytes([0xa5])*384
    container[444:828] = bytes([0x5a])*384
    struct.pack_into('<6I', container, 0, 0x10de, 1, (len(container)+255)&-256,
                     24, image_offset, image_bytes)
    struct.pack_into('<9I', container, 24, 60, 768, 828, 832, 836, 12, 848, 852, 36)
    struct.pack_into('<6I', container, 828, dmem_offset+16, 0, 1, 1, 3, 2)
    struct.pack_into('<9I', container, 852, 0, 256, dmem_offset, dmem_bytes,
                     1, 256, imem_bytes, 256, 0)
    return container


class Sec2BooterLayout(unittest.TestCase):
    def test_returns_payload_relative_ranges_without_mutating_the_container(self):
        image = booter()
        original = bytes(image)
        self.assertEqual(sec2_booter_layout(image), {
            'image_offset': 888,
            'imem': {'offset': 256, 'bytes': 512},
            'dmem': {'offset': 768, 'bytes': 768},
            'bootvec': 256,
            'signature': {'source': 60, 'dmem_offset': 16, 'bytes': 384,
                          'count': 2, 'fuse_versions': 1},
            'engine_mask': 1,
            'ucode_id': 3,
        })
        self.assertEqual(image, original)

    def test_rejects_truncation_and_invalid_geometry(self):
        with self.assertRaises(ValueError):
            sec2_booter_layout(booter()[:-1])
        for offset, value in ((24, 64), (28, 0), (48, 820), (828, 500), (832, 384),
                              (840, 0x400), (848, 0), (868, 2), (872, 512)):
            with self.subTest(offset=offset):
                image = booter()
                struct.pack_into('<I', image, offset, value)
                with self.assertRaises(ValueError):
                    sec2_booter_layout(image)

    def test_materializes_the_fallback_and_versioned_production_signatures(self):
        source = booter()
        original = bytes(source)
        for fuse_word, expected_index, signature_byte in ((0, 1, 0x5a), (1, 0, 0xa5), (0x10000, 1, 0x5a)):
            with self.subTest(fuse_word=fuse_word):
                image, receipt = prepare_sec2_booter(source, fuse_word)
                slot = 784
                self.assertEqual(len(image), 4096)
                self.assertEqual(receipt['signature_index'], expected_index)
                self.assertEqual(receipt['fuse_register'], 0x824148)
                self.assertEqual(image[:slot], original[888:888 + slot])
                self.assertEqual(image[slot:slot + 384], bytes([signature_byte])*384)
                self.assertEqual(image[slot + 384:1536], original[888 + slot + 384:])
                self.assertFalse(any(image[1536:]))
                self.assertEqual(source, original)

    def test_does_not_select_a_signature_for_invalid_or_unsupported_fuse_reads(self):
        for word in (None, -1, 2, 0xffffffff, 0xbadf5620, 0x100000000):
            with self.subTest(word=word):
                with self.assertRaises(ValueError):
                    prepare_sec2_booter(booter(), word)
