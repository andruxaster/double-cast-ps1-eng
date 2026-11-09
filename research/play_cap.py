import os,sys;sys.path.insert(0,os.path.dirname(os.path.abspath(__file__)))
from nav import *
from PIL import Image
def capture(e,tag,iters=80,every=6,step=25,maxshots=16):
    ps=[];last=None
    for i in range(iters):
        if i%every==every-1: e.tap('A',3,0)
        e.run(step)
        p=f'out/{tag}_{i:03d}.png'; im=e.shot(p)
        box=im.convert('L').crop((0,int(im.height*0.69),im.width,im.height))
        if box.getextrema()[1]>200:
            sig=box.resize((40,8)).tobytes()
            if sig!=last: ps.append(p); last=sig
    ps=ps[:maxshots]
    if ps: 
        ims=[Image.open(p).convert('RGB') for p in ps]
        W=ims[0].width; m=Image.new('RGB',(W*2,len(ims)*int(ims[0].height*0.31)*2))
        y=0
        for im in ims:
            c=im.crop((0,int(im.height*0.69),W,im.height)); c=c.resize((W*2,c.height*2),Image.NEAREST); m.paste(c,(0,y)); y+=c.height
        m.save(f'out/{tag}_text.png')
    return ps
if __name__=='__main__':
    cue=sys.argv[1]; tag=sys.argv[2]; st=sys.argv[3] if len(sys.argv)>3 else None
    e=Emu(cue)
    if st: e.run(5); e.load_state(open(st,'rb').read())
    else:
        e.run(900)
        for t in range(16): e.tap('A',3,120)
        e.tap('START',3,150)
    print(len(capture(e,tag)))
