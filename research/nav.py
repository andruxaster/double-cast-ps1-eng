import os,sys;sys.path.insert(0,os.path.dirname(os.path.abspath(__file__)))
from lr import Emu
from PIL import Image
def grid(paths,out,cols=4):
    ims=[Image.open(p).convert('RGB').resize((320,240)) for p in paths]
    rows=(len(ims)+cols-1)//cols
    m=Image.new('RGB',(320*cols,240*rows))
    for i,im in enumerate(ims): m.paste(im,((i%cols)*320,(i//cols)*240))
    m.save(out)
