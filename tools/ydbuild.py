# Disc rebuild helpers for YaruDora: Double Cast (PS1)
import struct, shutil, os
from disc import Disc
from ssc import SSC, tokens

def iso_files(d):
    """{'/S001/SCN001.SSC': (lba,size)} from the ISO9660 tree"""
    out = {}
    def walk(lba, size, path):
        data = d.read(lba, size); i = 0
        while i < len(data):
            l = data[i]
            if l == 0: i = (i//2048 + 1)*2048; continue
            rec = data[i:i+l]; i += l
            ext = struct.unpack('<I', rec[2:6])[0]; sz = struct.unpack('<I', rec[10:14])[0]
            nl = rec[32]; nm = rec[33:33+nl]
            if nm in (b'\0', b'\1'): continue
            nm = nm.decode('latin1').split(';')[0]
            if rec[25] & 2: walk(ext, sz, path + '/' + nm)
            else: out[path + '/' + nm] = (ext, sz)
    p = d.read(16, 2048); root = p[156:190]
    walk(struct.unpack('<I', root[2:6])[0], struct.unpack('<I', root[10:14])[0], '')
    return out

def rebuild_ssc(data, newstr):
    """newstr: {string_offset: bytes}. Rebuilds the string table and repoints 0x1A operands."""
    s = SSC(data); st = s.strings()
    table = bytearray(); remap = {}
    for k in sorted(st):
        remap[k] = len(table); table += newstr.get(k, st[k]) + b'\0'
    while len(table) % 16: table += b'\0'
    if len(table) > 0xffff: raise ValueError('string table > 64KB')
    code = bytearray(s.code)
    for o, b, a in tokens(s.code):
        if b == 0x1a:
            code[o+1:o+3] = struct.pack('<H', remap[struct.unpack('<H', a)[0]])
    h = list(s.h); h[7] = len(table); h[3] = len(code) + len(table); h[2] = 0x30 + h[3]
    return struct.pack('<12I', *h) + bytes(code) + bytes(table)

def _vfile_patch(vf, name, lba, size, payload):
    k = vf.find(name.encode() + b'\0')
    if k < 0: return
    rec = k - 2
    vf[rec+16:rec+20] = struct.pack('<I', lba); vf[rec+24:rec+28] = struct.pack('<I', size)
    if payload is not None: vf[rec+20:rec+24] = struct.pack('<I', payload)

def build_disc(src_bin, files, out_bin):
    """files: {iso_path: new_bytes}. Grown files are moved to the end of the image."""
    shutil.copyfile(src_bin, out_bin)
    d = Disc(out_bin); L = iso_files(d)
    vlba, vsize = L['/VFILE.INF']; vf = bytearray(d.read(vlba, vsize))
    nxt = d.nsec
    for path, data in files.items():
        lba, size = L[path]
        if (len(data)+2047)//2048 <= (size+2047)//2048:
            newlba = lba
        else:
            newlba = nxt; nxt += (len(data)+2047)//2048
        d.write_file(newlba, data)
        d.set_record(path, newlba, len(data))
        pl = struct.unpack('<I', data[12:16])[0] if data[:2] == b'\x83\xa1' else None
        _vfile_patch(vf, path.split('/')[-1], newlba, len(data), pl)
    d.write_file(vlba, bytes(vf))
    d.set_volsize(); d.f.close()
    cue = out_bin[:-4] + '.cue'
    with open(cue, 'w') as f:
        f.write('FILE "%s" BINARY\n  TRACK 01 MODE2/2352\n    INDEX 01 00:00:00\n' % os.path.basename(out_bin))
    return cue

def patch_exe(exe, ui):
    """ui: list of (file_offset, original_len, new_bytes)"""
    exe = bytearray(exe)
    def put(addr, words):
        o = 0x800 + addr - 0x80010000
        for i, w in enumerate(words): exe[o+i*4:o+i*4+4] = struct.pack('<I', w)
    # half-width -> SJIS converter (0x80029224): return the byte unchanged,
    # so 0xA0..0xDF are drawn from FONTA.DAT (6px Cyrillic)
    put(0x80029224, [0x03e00008, 0x00801021])
    # word wrap hook (see wordwrap.py): 0x800289FC -> j 0x8002922C
    import wordwrap, mini_asm
    hook = mini_asm.assemble(wordwrap.HOOK_ASM, wordwrap.HOOK_ADDR)
    assert len(hook) <= 0x800292f8 - wordwrap.HOOK_ADDR
    o = 0x800 + wordwrap.HOOK_ADDR - 0x80010000; exe[o:o+len(hook)] = hook
    put(0x800289fc, [0x08000000 | ((wordwrap.HOOK_ADDR >> 2) & 0x3ffffff), 0])
    for off, ln, nb in ui:
        if len(nb) > ln: raise ValueError('EXE string at %x too long (%d > %d)' % (off, len(nb), ln))
        exe[off:off+ln] = nb + b'\0'*(ln-len(nb))
    return bytes(exe)

def default_text_voice(data):
    """STARTUP.SSC / MAIN.SSC: in the settings-defaults block (vol 0x46,0x5F,0x7F ...)
    variable 0x38A (message mode: 0=voice only, 1=text+voice, 2=text only) is set to 0.
    Change 'push 0' (0x09) to 'push 1' (0x0A) so subtitles are on by default."""
    s = SSC(data); t = list(tokens(s.code)); code = bytearray(s.code); n = 0
    for i in range(len(t) - 3):
        if t[i][1] == 0x0b and t[i][2] == b'\x46' and t[i+1][1] == 0x70 and t[i+3][1] == 0x11 and t[i+3][2] == b'\x85\x03':
            for j in range(i, min(i + 40, len(t) - 3)):
                if t[j][1] == 0x09 and t[j+1][1] == 0x70 and t[j+2][1] == 0x03 and t[j+3][1] == 0x11 and t[j+3][2] == b'\x8a\x03':
                    code[t[j][0]] = 0x0a; n += 1; break
    out = bytearray(data); out[s.cs:s.cs+s.cl] = code
    return bytes(out), n
