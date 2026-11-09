import capstone,struct,sys,os
D=open(os.environ.get('YD_EXE','SCPS_100.53'),'rb').read()[0x800:]
BASE=0x80010000
md=capstone.Cs(capstone.CS_ARCH_MIPS,capstone.CS_MODE_MIPS32+capstone.CS_MODE_LITTLE_ENDIAN)
def dis(a,n):
    o=a-BASE
    for i in md.disasm(D[o:o+n*4],a): print('%08x  %s %s'%(i.address,i.mnemonic,i.op_str))
def w(a): return struct.unpack('<I',D[a-BASE:a-BASE+4])[0]
def refs(target):
    hi=(target+0x8000)>>16; lo=target&0xffff
    res=[]
    for o in range(0,len(D)-4,4):
        ins=struct.unpack('<I',D[o:o+4])[0]
        if (ins>>26)==0x0f and (ins&0xffff)==hi:
            # look ahead for lo
            for k in range(1,12):
                j=struct.unpack('<I',D[o+4*k:o+4*k+4])[0]
                if (j&0xffff)==lo: res.append(BASE+o); break
    return res
if __name__=='__main__':
    cmd=sys.argv[1]
    if cmd=='dis': dis(int(sys.argv[2],16),int(sys.argv[3]))
    if cmd=='refs': print([hex(x) for x in refs(int(sys.argv[2],16))])
