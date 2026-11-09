import sys,ctypes as C,bisect;sys.path.insert(0,os.path.dirname(os.path.abspath(__file__)))
from nav import *
def files_by_lba(disc):
    ents=[]
    for l in open(os.environ.get('YD_LST','disc%d.lst' % disc)):
        e=l.split()
        if e[3]=='0': ents.append((int(e[1]),int(e[2]),e[0]))
    ents.sort(); return ents
def lookup(ents,lba):
    i=bisect.bisect_right([e[0] for e in ents],lba)-1
    if i>=0 and lba < ents[i][0]+(ents[i][1]+2047)//2048: return ents[i]
def bcd(x): return (x>>4)*10+(x&15)
def dma_files(e,ents):
    n=C.c_uint.in_dll(e.lib,'g_dmalog_n').value
    log=(C.c_uint*(8192*3)).in_dll(e.lib,'g_dmalog')
    res={}
    for i in range(n):
        msf,madr,size=log[i*3],log[i*3+1],log[i*3+2]
        m,s,f=bcd(msf>>16),bcd((msf>>8)&0xff),bcd(msf&0xff)
        lba=(m*60+s)*75+f-150
        fe=lookup(ents,lba)
        if fe: res.setdefault(fe[2],[]).append((lba-fe[0],madr&0xffffff,madr>>24,size))
    return res
