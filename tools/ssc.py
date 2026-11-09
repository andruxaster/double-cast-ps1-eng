import struct
OPS={0x0b:1,0x0c:1,0x0d:2,0x0e:2,0x0f:4,0x10:1,0x11:2,0x12:1,0x13:1,0x14:1,0x1a:2,0x22:2,0x50:1}
def tsz(b): return 1 if (b&3) in (0,1) else (b&3)
def tokens(code):
    """yield (offset, opcode, operand bytes)"""
    i=0;n=len(code)
    while i<n:
        b=code[i]; j=i+1
        if b in OPS: j+=OPS[b]
        elif b==0x1e: j+=tsz(b)
        elif 0x80<=b<=0x8b: j+=tsz(b)
        elif b==0x90 or b==0x91: j+=1+tsz(code[i+1])
        elif b==0x92: j+=2+tsz(code[i+2])
        elif b>=0xe0: j+=1
        yield i,b,code[i+1:j]
        i=j
class SSC:
    def __init__(s,data):
        s.raw=bytearray(data)
        h=struct.unpack('<12I',data[:48]); s.h=list(h)
        s.cs=h[4]; s.cl=h[6]; s.sl=h[7]
        s.code=bytearray(data[s.cs:s.cs+s.cl])
        s.st=bytes(data[s.cs+s.cl:s.cs+s.cl+s.sl])
        s.tail=bytes(data[s.cs+s.cl+s.sl:])
    def strings(s):
        out={};i=0
        while i<len(s.st):
            j=s.st.index(0,i); out[i]=s.st[i:j]; i=j+1
        return out
    def refs(s):
        return [(o,struct.unpack('<H',a)[0]) for o,b,a in tokens(s.code) if b==0x1a]
