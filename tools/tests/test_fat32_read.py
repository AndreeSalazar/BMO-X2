"""Read-only FAT32 chain validation on a sparse synthetic image, never a device."""
from pathlib import Path
import struct
import sys
import tempfile
import unittest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'boot'))
from fat32_read import Fat32

class FatRead(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.path=Path(self.temp.name)/'disk.img'
        self.base=2048*512;self.fat=self.base+32*512;self.fat_size=513*512;self.data=self.fat+2*self.fat_size
        total=32+1026+65525
        with self.path.open('wb') as f:f.truncate(self.base+total*512)
        self.write(512,b'EFI PART');self.write(512+72,struct.pack('<Q',2))
        self.write(1024+32,struct.pack('<QQ',2048,2048+total-1))
        b=bytearray(512);struct.pack_into('<H',b,11,512);b[13]=1;struct.pack_into('<H',b,14,32);b[16]=2
        struct.pack_into('<II4xI',b,32,total,513,2);self.write(self.base,b)
        for index,value in [(2,0xfffffff),(3,4),(4,0xfffffff)]:self.entry(index,value)
        record=bytearray(32);record[:11]=b'PAYLOAD BIN';record[11]=32
        struct.pack_into('<H',record,26,3);struct.pack_into('<I',record,28,600)
        self.write(self.data,record);self.write(self.data+512,b'A'*512);self.write(self.data+1024,b'B'*512)
    def write(self,at,data):
        with self.path.open('r+b') as f:f.seek(at);f.write(data)
    def entry(self,index,value):
        for offset in (self.fat,self.fat+self.fat_size):self.write(offset+index*4,struct.pack('<I',value))
    def tearDown(self):self.temp.cleanup()
    def test_exact_chain_and_file_limit(self):
        fs=Fat32(self.path)
        try:
            self.assertEqual(fs.file_bytes('PAYLOAD.BIN'),b'A'*512+b'B'*88)
            with self.assertRaises(ValueError):fs.file_bytes('PAYLOAD.BIN',10)
            with self.assertRaises(ValueError):fs.file_bytes('MISSING.TXT')
        finally:fs.close()
    def test_mismatched_fat_mirrors(self):
        self.write(self.fat+self.fat_size+3*4,struct.pack('<I',5));fs=Fat32(self.path)
        try:
            with self.assertRaisesRegex(ValueError,'mirrors'):fs.file_bytes('PAYLOAD.BIN')
        finally:fs.close()
    def test_cycle_and_short_chain(self):
        self.entry(4,3);self.write(self.data+28,struct.pack('<I',1100));fs=Fat32(self.path)
        try:
            with self.assertRaisesRegex(ValueError,'cycle'):fs.file_bytes('PAYLOAD.BIN')
        finally:fs.close()
        self.entry(3,0xfffffff);fs=Fat32(self.path)
        try:
            with self.assertRaisesRegex(ValueError,'Short'):fs.file_bytes('PAYLOAD.BIN')
        finally:fs.close()
    def test_small_table_is_rejected(self):
        self.write(self.base+36,struct.pack('<I',1))
        with self.assertRaises(ValueError):Fat32(self.path)

if __name__=='__main__':unittest.main()
