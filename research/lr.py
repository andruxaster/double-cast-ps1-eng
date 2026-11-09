import ctypes as C, sys, os, struct
from PIL import Image
import os
CORE=os.environ.get('PCSX_CORE', 'pcsx_rearmed_libretro.so')
class GameInfo(C.Structure): _fields_=[('path',C.c_char_p),('data',C.c_void_p),('size',C.c_size_t),('meta',C.c_char_p)]
class Var(C.Structure): _fields_=[('key',C.c_char_p),('value',C.c_char_p)]
ENVCB=C.CFUNCTYPE(C.c_bool,C.c_uint,C.c_void_p)
VIDCB=C.CFUNCTYPE(None,C.c_void_p,C.c_uint,C.c_uint,C.c_size_t)
AUDCB=C.CFUNCTYPE(None,C.c_int16,C.c_int16)
AUDBCB=C.CFUNCTYPE(C.c_size_t,C.c_void_p,C.c_size_t)
POLLCB=C.CFUNCTYPE(None)
INCB=C.CFUNCTYPE(C.c_int16,C.c_uint,C.c_uint,C.c_uint,C.c_uint)
LOGCB=C.CFUNCTYPE(None,C.c_int,C.c_char_p)
class LogIf(C.Structure): _fields_=[('log',C.c_void_p)]
BTN={'B':0,'Y':1,'SELECT':2,'START':3,'UP':4,'DOWN':5,'LEFT':6,'RIGHT':7,'A':8,'X':9,'L':10,'R':11,'L2':12,'R2':13}
# PS: B=Cross, A=Circle, Y=Square, X=Triangle
class Emu:
    def __init__(s,cue,opts=None):
        s.lib=C.CDLL(CORE)
        s.fmt=0; s.frame=None; s.pressed=set()
        s.opts={b'pcsx_rearmed_bios':b'HLE',b'pcsx_rearmed_drc':b'enabled'}
        if opts: s.opts.update(opts)
        s._keep=[]
        s.sysdir=C.c_char_p(os.environ.get('PCSX_SYSDIR','.').encode()); s.savedir=C.c_char_p(os.environ.get('PCSX_SAVEDIR','.').encode())
        def env(cmd,data):
            cmd&=0xffff
            if cmd==9:  # system dir
                C.cast(data,C.POINTER(C.c_char_p))[0]=s.sysdir.value; return True
            if cmd==31:
                C.cast(data,C.POINTER(C.c_char_p))[0]=s.savedir.value; return True
            if cmd==10:
                s.fmt=C.cast(data,C.POINTER(C.c_int))[0]; return True
            if cmd==15:
                v=C.cast(data,C.POINTER(Var))[0]
                val=s.opts.get(v.key)
                if val is not None:
                    C.cast(data,C.POINTER(Var))[0].value=val; return True
                return False
            if cmd==27:
                lg=LogIf(); lg.log=C.cast(s._logcb,C.c_void_p)
                C.cast(data,C.POINTER(LogIf))[0]=lg; return True
            if cmd==3: C.cast(data,C.POINTER(C.c_bool))[0]=True; return True
            return False
        def vid(data,w,h,pitch):
            if data:
                s.frame=(C.string_at(data,pitch*h),w,h,pitch)
        def logf(level,msg):
            if level>=2: sys.stderr.write('[core] '+msg.decode(errors='replace'))
        s._logcb=LOGCB(logf)
        s._env=ENVCB(env); s._vid=VIDCB(vid); s._aud=AUDCB(lambda l,r:None)
        s._audb=AUDBCB(lambda d,n:n); s._poll=POLLCB(lambda:None)
        s._in=INCB(lambda port,dev,idx,id_: 1 if (port==0 and dev==1 and id_ in s.pressed) else 0)
        s.lib.retro_set_environment(s._env)
        s.lib.retro_init()
        s.lib.retro_set_video_refresh(s._vid); s.lib.retro_set_audio_sample(s._aud)
        s.lib.retro_set_audio_sample_batch(s._audb); s.lib.retro_set_input_poll(s._poll); s.lib.retro_set_input_state(s._in)
        gi=GameInfo(cue.encode(),None,0,None)
        s.lib.retro_load_game.argtypes=[C.POINTER(GameInfo)]
        assert s.lib.retro_load_game(C.byref(gi)),'load failed'
        s.lib.retro_get_memory_data.restype=C.c_void_p
        s.nframes=0
    def run(s,n=1,press=()):
        s.pressed={BTN[b] for b in press}
        for _ in range(n): s.lib.retro_run(); s.nframes+=1
        s.pressed=set()
    def tap(s,b,hold=3,after=20):
        s.run(hold,(b,)); s.run(after)
    def ram(s):
        p=s.lib.retro_get_memory_data(2); return C.string_at(p,0x200000)
    def wram(s,addr,data):
        p=s.lib.retro_get_memory_data(2); C.memmove(p+(addr&0x1fffff),data,len(data))
    def shot(s,path):
        data,w,h,pitch=s.frame
        if s.fmt==1:  # XRGB8888
            img=Image.frombuffer('RGBX',(w,h),data,'raw','BGRX',pitch,1).convert('RGB')
        else:  # RGB565
            img=Image.frombuffer('RGB',(w,h),data,'raw','BGR;16',pitch,1)
        img.save(path); return img
    def save_state(s):
        s.lib.retro_serialize_size.restype=C.c_size_t
        n=s.lib.retro_serialize_size(); buf=C.create_string_buffer(n)
        assert s.lib.retro_serialize(buf,C.c_size_t(n)); return buf.raw
    def load_state(s,raw):
        buf=C.create_string_buffer(raw,len(raw)); assert s.lib.retro_unserialize(buf,C.c_size_t(len(raw)))
