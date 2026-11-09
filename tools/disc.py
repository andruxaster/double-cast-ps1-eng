import struct, shutil, os
# --- EDC/ECC for CD-ROM ---
def _tables():
    ecc_f=[0]*256; ecc_b=[0]*256; edc=[0]*256
    for i in range(256):
        j=(i<<1)^(0x11d if i&0x80 else 0)
        ecc_f[i]=j&0xff; ecc_b[i^j&0xff]=i
        e=i
        for _ in range(8): e=(e>>1)^(0xd8018001 if e&1 else 0)
        edc[i]=e
    return ecc_f,ecc_b,edc
ECC_F,ECC_B,EDC=_tables()
def edc_calc(data):
    e=0
    for b in data: e=(e>>8)^EDC[(e^b)&0xff]
    return e
def _ecc_pq(sec,major_count,minor_count,major_mult,minor_inc,dest):
    size=major_count*minor_count
    for major in range(major_count):
        index=(major>>1)*major_mult+(major&1)
        ea=0; eb=0
        for minor in range(minor_count):
            temp=sec[0xC+index]
            index+=minor_inc
            if index>=size: index-=size
            ea^=temp; eb^=temp; ea=ECC_F[ea]
        ea=ECC_B[ECC_F[ea]^eb]
        sec[dest+major]=ea; sec[dest+major+major_count]=ea^eb
def encode_form1(sec):
    """sec: bytearray(2352) with sync/header/subheader/data filled; mode2 form1"""
    e=edc_calc(sec[0x10:0x818]); sec[0x818:0x81c]=struct.pack('<I',e)
    hdr=bytes(sec[0xC:0x10]); sec[0xC:0x10]=b'\0\0\0\0'
    _ecc_pq(sec,86,24,2,86,0x81c)
    _ecc_pq(sec,52,43,86,88,0x8c8)
    sec[0xC:0x10]=hdr
class Disc:
    def __init__(s,path):
        s.path=path; s.f=open(path,'r+b')
        s.nsec=os.path.getsize(path)//2352
    def raw(s,lba):
        s.f.seek(lba*2352); return bytearray(s.f.read(2352))
    def read(s,lba,size):
        out=b''
        for i in range((size+2047)//2048): out+=bytes(s.raw(lba+i)[24:2072])
        return out[:size]
    def write_sector(s,lba,data2048,sub=None,eof=False):
        if lba<s.nsec: sec=s.raw(lba)
        else:
            sec=bytearray(2352); sec[0:12]=b'\x00'+b'\xff'*10+b'\x00'
            m=lba+150; sec[12:16]=bytes([int(str(m//4500),16),int(str((m//75)%60),16),int(str(m%75),16),2])
            sec[16:24]=b'\x00\x00\x08\x00'*2
        if sub is not None: sec[16:24]=sub*2
        if eof:
            sub2=bytearray(sec[16:20]); sub2[2]|=0x81; sec[16:24]=bytes(sub2)*2
        sec[24:2072]=data2048.ljust(2048,b'\0')
        encode_form1(sec)
        s.f.seek(lba*2352); s.f.write(sec)
        s.nsec=max(s.nsec,lba+1)
    def write_file(s,lba,data):
        n=(len(data)+2047)//2048
        for i in range(n):
            last=(i==n-1)
            sub=b'\x00\x00\x89\x00' if last else b'\x00\x00\x08\x00'
            s.write_sector(lba+i,data[i*2048:(i+1)*2048],sub=sub)
    # ISO9660 directory record patch
    def find_record(s,path):
        p=s.read(16,2048); root=p[156:190]
        lba=struct.unpack('<I',root[2:6])[0]; size=struct.unpack('<I',root[10:14])[0]
        parts=path.strip('/').split('/')
        for k,part in enumerate(parts):
            found=None
            for sec in range((size+2047)//2048):
                d=s.read(lba+sec,2048); i=0
                while i<2048 and d[i]:
                    l=d[i]; rec=d[i:i+l]; nl=rec[32]; nm=rec[33:33+nl].decode('latin1')
                    if nm.split(';')[0]==part:
                        found=(lba+sec,i,rec)
                        break
                    i+=l
                if found: break
            if not found: raise KeyError(path)
            if k<len(parts)-1:
                rec=found[2]; lba=struct.unpack('<I',rec[2:6])[0]; size=struct.unpack('<I',rec[10:14])[0]
        return found
    def set_record(s,path,newlba,newsize):
        sl,off,rec=s.find_record(path)
        d=bytearray(s.read(sl,2048))
        d[off+2:off+10]=struct.pack('<I',newlba)+struct.pack('>I',newlba)
        d[off+10:off+18]=struct.pack('<I',newsize)+struct.pack('>I',newsize)
        sub=bytes(s.raw(sl)[16:20])
        s.write_sector(sl,bytes(d),sub=sub)
    def set_volsize(s):
        d=bytearray(s.read(16,2048)); d[80:88]=struct.pack('<I',s.nsec)+struct.pack('>I',s.nsec)
        s.write_sector(16,bytes(d),sub=bytes(s.raw(16)[16:20]))
