#!/usr/bin/env python3
"""Переносит английский фан-перевод PSP-версии (Cargodin & Esperknight) на PS1-диски.
   python3 port_english.py CD1.bin CD2.bin "Yarudora Portable - Double Cast.iso" patch.xdelta3 outdir
Нужен xdelta3 в PATH (для наложения PSP-патча и создания PS1-патчей)."""
import sys, os, struct, subprocess, shutil, tempfile, re
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), 'tools'))
from common import load_scripts, classify
from ssc import SSC
from jdec import dec
from ydtext import enc_en, wrap, hw2fw, build_fonta_en, MAXLINES
from ydbuild import rebuild_ssc, build_disc, patch_exe, default_text_voice
from psp_en import build_map, decode_en
import ui_en

def iso2048_files(path):
    f = open(path, 'rb')
    def sec(n, c=1): f.seek(n*2048); return f.read(2048*c)
    p = sec(16); root = p[156:190]; out = {}
    def walk(lba, size, pth):
        d = sec(lba, (size+2047)//2048); i = 0
        while i < len(d):
            l = d[i]
            if l == 0: i = (i//2048+1)*2048; continue
            r = d[i:i+l]; i += l
            e = struct.unpack('<I', r[2:6])[0]; s = struct.unpack('<I', r[10:14])[0]; nm = r[33:33+r[32]]
            if nm in (b'\0', b'\1'): continue
            nm = nm.decode('latin1').split(';')[0]
            if r[25] & 2: walk(e, s, pth + '/' + nm)
            else: out[pth + '/' + nm] = (e, s)
    walk(struct.unpack('<I', root[2:6])[0], struct.unpack('<I', root[10:14])[0], '')
    return f, out

def psp_ssc(iso, tmp, tag):
    f, L = iso2048_files(iso); res = []
    for k in sorted(L):
        if '/IGX001/' in k and k.endswith('.SSC'):
            f.seek(L[k][0]*2048); p = os.path.join(tmp, tag + k.replace('/', '_'))
            open(p, 'wb').write(f.read(L[k][1])); res.append(p)
    return res

def clean_en(t):
    t = t.replace('\x00$', ' ')             # PSP line breaks -> spaces (engine word-wraps now)
    t = re.sub(r'\x00.', '', t)              # drop remaining inline engine codes
    t = re.sub(r'  +', ' ', t).rstrip()
    return t                                  # a leading space = continuation of the previous piece

def main(cd1, cd2, psp_iso, psp_patch, outdir):
    os.makedirs(outdir, exist_ok=True)
    tmp = tempfile.mkdtemp()
    en_iso = os.path.join(tmp, 'en.iso')
    subprocess.run(['xdelta3', '-d', '-f', '-s', psp_iso, psp_patch, en_iso], check=True)
    J = psp_ssc(psp_iso, tmp, 'jp'); E = psp_ssc(en_iso, tmp, 'en')
    os.remove(en_iso)
    m = build_map(J, E)
    warn = []
    for n, src in ((1, cd1), (2, cd2)):
        sc = load_scripts(src); files = {}; done = total = 0
        for p, data in sc.items():
            if p.startswith('__'): continue
            if p.endswith(('STARTUP.SSC', 'MAIN.SSC')): data = default_text_voice(data)[0]  # subtitles on by default
            s = SSC(data); new = {}
            for k, v in s.strings().items():
                t = dec(v)
                kind, body, pre, suf = classify(t)
                if kind in (None, 'skip') or body is None or not any(c >= 0x80 for c in v):
                    if any(0xa1 <= c <= 0xdf for c in v): new[k] = hw2fw(v)
                    continue
                total += 1; en = None
                if v in m:
                    en = clean_en(decode_en(m[v])[0])
                    if kind == 'name': en = re.sub(r'^D\d', '', en)
                else:
                    st = body.lstrip('　 ')
                    if st in ui_en.SYSTEM: en = ui_en.SYSTEM[st]
                if not en:
                    new[k] = hw2fw(v); continue
                if kind == 'name':
                    new[k] = pre.encode() + enc_en(en); done += 1; continue
                if len(wrap(en.strip())) > MAXLINES: warn.append('%s: ~%d lines: %s' % (p, len(wrap(en.strip())), en.strip()))
                new[k] = pre.encode('ascii') + enc_en(en) + suf.encode('ascii'); done += 1
            files[p] = rebuild_ssc(data, new)
        exe_path, exe = sc['__exe__']
        ui = []
        for off, pre, txt, suf in ui_en.EXE_UI:
            nb = pre.encode() + b'%d'.join(enc_en(x) if '{' not in x else x.encode() for x in txt.split('%d')) + suf.encode()
            if '{' in txt:
                a, b = txt.split('{', 1); b, c = b.split('}', 1)
                nb = pre.encode() + enc_en(a) + b'{' + b.encode() + b'}' + enc_en(c) + suf.encode()
            ui.append((off, exe.index(b'\0', off) - off, nb))
        files[exe_path] = patch_exe(exe, ui)
        files['/SYSTEM/FONTA.DAT'] = build_fonta_en(sc['__fonta__'])
        out = os.path.join(outdir, 'Double Cast (CD%d) [EN].bin' % n)
        build_disc(src, files, out)
        print('CD%d: %d/%d строк на английском -> %s' % (n, done, total, out))
        xd = os.path.join(outdir, 'DoubleCast_CD%d_EN_PS1.xdelta' % n)
        subprocess.run(['xdelta3', '-e', '-9', '-f', '-S', 'djw', '-s', src, out, xd], check=True)
    shutil.rmtree(tmp)
    if warn:
        open(os.path.join(outdir, 'warnings_en.txt'), 'w', encoding='utf-8').write('\n'.join(warn))
        print('длинных реплик (>3 строк):', len(warn))

if __name__ == '__main__':
    main(*sys.argv[1:6])
