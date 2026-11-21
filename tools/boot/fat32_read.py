"""Bounded read-only GPT/FAT32 inspection for generated boot images."""
from pathlib import Path
import struct

class Fat32:
    def __init__(self,path):
        self.path=Path(path);self.file=self.path.open('rb');self.length=self.path.stat().st_size
        try:self._geometry()
        except BaseException:self.file.close();raise
    def _geometry(self):
        gpt=self.read(512,512)
        if gpt[:8]!=b'EFI PART':raise ValueError('GPT signature')
        table=self.read(struct.unpack_from('<Q',gpt,72)[0]*512,128)
        self.base=struct.unpack_from('<Q',table,32)[0]*512
        self.end=(struct.unpack_from('<Q',table,40)[0]+1)*512
        bpb=self.read(self.base,512)
        sector=struct.unpack_from('<H',bpb,11)[0];spc=bpb[13];reserved=struct.unpack_from('<H',bpb,14)[0]
        self.fats=bpb[16];total,fat_size,self.root=struct.unpack_from('<II4xI',bpb,32)
        if sector!=512 or not 1<=spc<=128 or spc&(spc-1) or not reserved or self.fats!=2 or not fat_size or total*512>self.end-self.base:
            raise ValueError('FAT32 geometry')
        self.cluster=spc*512;self.fat_offset=self.base+reserved*512;self.fat_bytes=fat_size*512
        self.data=self.base+(reserved+self.fats*fat_size)*512
        self.count=(self.base+total*512-self.data)//self.cluster
        if not 65525<=self.count<0x0ffffff5 or self.fat_bytes//4<self.count+2 or not 2<=self.root<self.count+2:
            raise ValueError('Not FAT32 cluster count/table')
    def read(self,offset,size):
        if offset<0 or size<0 or offset+size>self.length:raise ValueError('Image bounds')
        self.file.seek(offset);data=self.file.read(size)
        if len(data)!=size:raise ValueError('Truncated image')
        return data
    def chain(self,start,maximum=16385):
        seen=set();cluster=start
        while cluster<0xffffff8:
            if not 2<=cluster<self.count+2 or cluster in seen or len(seen)>=maximum:raise ValueError('FAT chain bounds/cycle')
            seen.add(cluster)
            offset=self.data+(cluster-2)*self.cluster
            if offset+self.cluster>self.end:raise ValueError('Partition bounds')
            a=self.read(self.fat_offset+cluster*4,4)
            b=self.read(self.fat_offset+self.fat_bytes+cluster*4,4)
            if a!=b:raise ValueError('FAT mirrors differ')
            yield self.read(offset,self.cluster)
            cluster=struct.unpack('<I',a)[0]&0xfffffff
    def file_bytes(self,path,limit=2*1024*1024):
        parts=path.split('/');cluster=self.root
        for index,part in enumerate(parts):
            name,_,extension=part.upper().partition('.')
            if not name or len(name)>8 or len(extension)>3:raise ValueError('Expected short FAT name')
            key=(name.ljust(8)+extension.ljust(3)).encode('ascii');found=None
            for block in self.chain(cluster):
                for at in range(0,len(block),32):
                    entry=block[at:at+32]
                    if entry[:11]==key and entry[11]!=15:found=entry;break
                if found:break
            if found is None:raise ValueError('Missing FAT path: '+path)
            cluster=(struct.unpack_from('<H',found,20)[0]<<16)|struct.unpack_from('<H',found,26)[0]
            if index<len(parts)-1:
                if not found[11]&16:raise ValueError('FAT parent is not a directory')
            else:
                size=struct.unpack_from('<I',found,28)[0]
                if found[11]&16 or size>limit:raise ValueError('FAT file bounds')
                data=bytearray()
                clusters=max(1,(size+self.cluster-1)//self.cluster)
                for block in self.chain(cluster,clusters):
                    data.extend(block)
                    if len(data)>=size:break
                if len(data)<size:raise ValueError('Short FAT file')
                return bytes(data[:size])
    def close(self):self.file.close()
