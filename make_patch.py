#!/usr/bin/env python3
"""Собирает русские образы YaruDora: Double Cast (PS1) из ваших образов и таблицы перевода.
   python3 make_patch.py CD1.bin CD2.bin script_ru.xlsx outdir
Строки без перевода остаются японскими (полуширинная кана автоматически переводится в полноширинную)."""
import sys, os, subprocess, shutil
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), 'tools'))
from openpyxl import load_workbook
from common import load_scripts, classify
from ssc import SSC
from jdec import dec
from ydtext import enc, wrap, hw2fw, build_fonta, MAXLINES
from ydbuild import rebuild_ssc, build_disc, patch_exe, default_text_voice
from ui_ru import EXE_UI, SYSTEM, NAMES

def load_table(path):
    wb = load_workbook(path, read_only=True)
    tr = {}
    for r in list(wb['Реплики'].iter_rows(min_row=2, values_only=True)):
        if r[4] and r[5] and str(r[5]).strip(): tr[str(r[4])] = str(r[5]).strip()
    names = dict(NAMES)
    for r in wb['Имена'].iter_rows(min_row=2, values_only=True):
        if r[0] and r[1]: names[str(r[0])] = str(r[1]).strip()
    return tr, names

def ru_bytes(ru):
    ru = ru.replace('\r', '')
    return enc(ru), len(wrap(ru.strip()))   # the engine word-wraps; wrap() only estimates line count

def translate_script(data, tr, names, warn, fname):
    s = SSC(data); new = {}; done = total = 0
    for k, v in s.strings().items():
        t = dec(v)
        kind, body, pre, suf = classify(t)
        if kind is None or kind == 'skip' or body is None:
            if any(0xa1 <= c <= 0xdf for c in v): new[k] = hw2fw(v)
            continue
        if not any(c >= 0x80 for c in v): continue
        total += 1
        ru = None
        if kind == 'name':
            ru = names.get(body)
            if ru is not None:
                new[k] = pre.encode() + enc(ru); done += 1; continue
        else:
            ru = tr.get(t)
            stripped = body.lstrip('　 ')
            if ru is None and stripped in SYSTEM: ru = SYSTEM[stripped]
            if ru is not None:
                lead = '' if kind in ('реплика', 'текст') else body[:len(body) - len(stripped)].replace('　', '  ')
                try:
                    b, n = ru_bytes(lead + ru)
                except ValueError as e:
                    warn.append('%s: %s' % (fname, e)); b = None
                if b is not None:
                    if n > MAXLINES: warn.append('%s: %d строк(и) (> %d, начало уедет за экран): %s' % (fname, n, MAXLINES, ru))
                    new[k] = pre.encode('ascii') + b + suf.encode('ascii'); done += 1; continue
        new[k] = hw2fw(v)
    return rebuild_ssc(data, new), done, total

def exe_ui():
    out = []
    for off, pre, ru, suf in EXE_UI:
        out.append((off, None, pre.encode() + b'%d'.join(enc(x) for x in ru.split('%d')) + suf.encode()))
    return out

def main(cd1, cd2, table, outdir):
    os.makedirs(outdir, exist_ok=True)
    tr, names = load_table(table)
    warn = []
    for n, src in ((1, cd1), (2, cd2)):
        sc = load_scripts(src)
        files = {}; d = t = 0
        for p, data in sc.items():
            if p.startswith('__'): continue
            if p.endswith(('STARTUP.SSC', 'MAIN.SSC')): data = default_text_voice(data)[0]  # subtitles on by default
            files[p], a, b = translate_script(data, tr, names, warn, p); d += a; t += b
        exe_path, exe = sc['__exe__']
        ui = []
        for off, _, nb in exe_ui():
            ln = exe.index(b'\0', off) - off
            ui.append((off, ln, nb))
        files[exe_path] = patch_exe(exe, ui)
        files['/SYSTEM/FONTA.DAT'] = build_fonta(sc['__fonta__'])
        out = os.path.join(outdir, 'Double Cast (CD%d) [RU].bin' % n)
        build_disc(src, files, out)
        print('CD%d: переведено %d из %d строк -> %s' % (n, d, t, out))
        if shutil.which('xdelta3'):
            xd = os.path.join(outdir, 'DoubleCast_CD%d_RU.xdelta' % n)
            subprocess.run(['xdelta3', '-e', '-9', '-f', '-S', 'djw', '-s', src, out, xd], check=True)
            print('  патч:', xd)
    if warn:
        with open(os.path.join(outdir, 'warnings.txt'), 'w', encoding='utf-8') as f: f.write('\n'.join(warn))
        print('предупреждений:', len(warn), '(см. warnings.txt)')

if __name__ == '__main__':
    main(*sys.argv[1:5])
