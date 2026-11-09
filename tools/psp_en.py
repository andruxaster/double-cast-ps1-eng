# Builds a Japanese->English string map from the PSP version
# (original Yarudora Portable ISO + the fan English xdelta patch). Same SSC engine as PS1.
import collections, difflib
from ssc import SSC, tokens

def _sz(data, base, off):
    return data[base+off:data.index(0, base+off)]

def pairs(jp_data, en_data):
    a = SSC(jp_data); b = SSC(en_data)
    ba = a.cs + a.cl; bb = b.cs + b.cl
    ta = list(tokens(a.code)); tb = list(tokens(b.code))
    key = lambda t: (t[1], b'' if t[1] == 0x1a else bytes(t[2]))
    sm = difflib.SequenceMatcher(None, [key(t) for t in ta], [key(t) for t in tb], autojunk=False)
    for i, j, n in sm.get_matching_blocks():
        for k in range(n):
            x, y = ta[i+k], tb[j+k]
            if x[1] == 0x1a:
                yield _sz(jp_data, ba, int.from_bytes(x[2], 'little')), _sz(en_data, bb, int.from_bytes(y[2], 'little'))

def build_map(jp_files, en_files):
    m = collections.defaultdict(collections.Counter)
    for jf, ef in zip(jp_files, en_files):
        for j, e in pairs(open(jf, 'rb').read(), open(ef, 'rb').read()):
            if j != e: m[j][e] += 1
    return {k: v.most_common(1)[0][0] for k, v in m.items()}

# --- decode the PSP English encoding to plain text (control codes kept as ASCII) ---
FW = {0x41: '"', 0x5b: '!', 0x5c: "'", 0x5d: '?', 0x5e: ',', 0x5f: '.', 0x40: ' ', 0x4c: '-',
      0x4e: '-', 0x47: '(', 0x48: ')', 0x49: '*', 0x43: '(', 0x59: ':', 0x60: '~', 0x65: '"', 0x66: '"'}
for _d in range(10): FW[0x4f + _d] = str(_d)
SJ = {b'\x81\x60': '~', b'\x81\x40': ' ', b'\x81\x65': "'", b'\x81\x66': "'"}
def decode_en(v):
    out = ''; i = 0; unk = []
    while i < len(v):
        c = v[i]
        if 0x81 <= c <= 0x9f or 0xe0 <= c <= 0xef:
            p = v[i:i+2]
            if c == 0x82 and p[1] in FW: out += FW[p[1]]
            elif p in SJ: out += SJ[p]
            else:
                try: out += p.decode('cp932')
                except UnicodeDecodeError: out += '?'; unk.append(p.hex())
            i += 2; continue
        if 0xa6 <= c <= 0xbf: out += chr(65 + c - 0xa6)
        elif 0xa0 <= c <= 0xa5: out += '?'; unk.append('%02x' % c)
        elif 0xc0 <= c <= 0xd9: out += chr(97 + c - 0xc0)
        elif c == 0xda: out += ' '
        elif c < 0x80: out += '\x00' + chr(c)      # engine control byte (ASCII), marked
        else: out += '?'; unk.append('%02x' % c)
        i += 1
    return out, unk
