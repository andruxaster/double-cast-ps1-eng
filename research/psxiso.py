import sys
class Bin:
    def __init__(s,path): s.f=open(path,'rb')
    def sec(s,n,raw=False):
        s.f.seek(n*2352); r=s.f.read(2352)
        return r if raw else r[24:24+2048]
    def read(s,lba,size):
        return b''.join(s.sec(lba+i) for i in range((size+2047)//2048))[:size]
    def files(s):
        p=s.sec(16); root=p[156:190]
        return s._dir(int.from_bytes(root[2:6],'little'),int.from_bytes(root[10:14],'little'),'')
    def _dir(s,lba,size,path):
        data=s.read(lba,size);i=0;out=[]
        while i<len(data):
            l=data[i]
            if l==0: i=(i//2048+1)*2048; continue
            rec=data[i:i+l]; i+=l
            ext=int.from_bytes(rec[2:6],'little'); sz=int.from_bytes(rec[10:14],'little'); fl=rec[25]; nl=rec[32]; nm=rec[33:33+nl]
            if nm in (b'\0',b'\1'): continue
            nm=nm.decode('latin1')
            # XA attr
            xa=rec[33+nl+(1-nl%2):]
            out.append((path+'/'+nm,ext,sz,fl,xa[4:6].hex() if len(xa)>=8 else ''))
            if fl&2: out+=s._dir(ext,sz,path+'/'+nm)
        return out
if __name__=='__main__':
    for e in Bin(sys.argv[1]).files(): print(*e)
