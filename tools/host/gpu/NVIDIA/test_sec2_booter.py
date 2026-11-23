import struct
import unittest

from .sec2_booter import sec2_booter_layout


def booter():
    image_offset = 888
    image_bytes = 1536
    container = bytearray(image_offset + image_bytes)
    struct.pack_into('<6I', container, 0, 0x10de, 1, 2560, 24, image_offset, image_bytes)
    struct.pack_into('<9I', container, 24, 60, 768, 828, 832, 836, 12, 848, 852, 36)
    struct.pack_into('<6I', container, 828, 784, 0, 1, 1, 3, 2)
    struct.pack_into('<9I', container, 852, 0, 256, 768, 768, 1, 256, 512, 256, 0)
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
