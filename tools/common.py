import re, os
from disc import Disc
from ssc import SSC
from jdec import dec
from ydbuild import iso_files
from ydtext import split_ctrl

JP = re.compile('[぀-ヿ一-鿿！-～]')
NAME = re.compile(r'^([@!&]*)D(\d)(.+)$')

def load_scripts(bin_path):
    d = Disc(bin_path); L = iso_files(d); out = {}
    for p, (lba, sz) in L.items():
        if p.endswith('.SSC'): out[p] = d.read(lba, sz)
    exe = [p for p in L if p.startswith('/SCPS_')][0]
    out['__exe__'] = (exe, d.read(*L[exe]))
    out['__fonta__'] = d.read(*L['/SYSTEM/FONTA.DAT'])
    d.f.close()
    return out

def classify(t):
    """returns (kind, body, prefix, suffix)"""
    if t.startswith('例外処理'): return 'skip', None, None, None
    m = NAME.match(t)
    if m: return 'name', m.group(3), m.group(1) + 'D' + m.group(2), ''
    pre, body, suf = split_ctrl(t)
    if body.startswith('「'): kind = 'реплика'
    elif body.startswith('　'): kind = 'текст'
    else: kind = 'выбор/прочее'
    return kind, body, pre, suf

def iter_lines(scripts):
    """yields (file, offset, decoded_text) for every Japanese string in script order"""
    for p in sorted(k for k in scripts if not k.startswith('__')):
        s = SSC(scripts[p])
        for k, v in sorted(s.strings().items()):
            t = dec(v)
            if JP.search(t): yield p, k, t
