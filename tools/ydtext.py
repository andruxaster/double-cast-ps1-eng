# Text codec for YaruDora: Double Cast (PS1) Russian patch
import re, unicodedata
from glyphs import GLYPHS

# --- Russian -> game bytes -------------------------------------------------
# Cyrillic is drawn by the 6x12 half-width font (FONTA.DAT):
#   Б..Я -> 0xA1..0xBF, а..я -> 0xC0..0xDF, А -> 0x7F (0xA0 is an escape byte in the engine)
# ASCII letters C D Q S T W (any case) and  ! # $ % & * / : @ | { }  are engine control codes,
# so "!" and ":" are remapped to free glyph slots 0x60 and 0x5E.
CTRL_ASCII = set('#$%&*/@|{}~CDQSTWcdqstw')
def enc(s):
    out = bytearray(); raw = False
    for ch in s:
        if raw or ch == '{':          # {...} = literal ASCII (engine raw mode)
            out += ch.encode('ascii'); raw = (ch != '}'); continue
        if ch == '\n': out += b'$'; continue
        if ch in 'Ёё': ch = 'Е' if ch == 'Ё' else 'е'
        o = ord(ch)
        if ch == 'А': out.append(0x7f)
        elif ch == '!': out.append(0x60)
        elif ch == ':': out.append(0x5e)
        elif 0x411 <= o <= 0x42f: out.append(0xa0 + o - 0x410)
        elif 0x430 <= o <= 0x44f: out.append(0xc0 + o - 0x430)
        elif ch in '«»“”„': out += b'"'
        elif ch in '’‘': out += b"'"
        elif ch in '—–': out += b'-'
        elif ch == '…': out += b'...'
        elif ch == '～': out += b'\x81\x60'
        elif ch == '♪': out += b'\x81\xf4'
        elif o < 0x80:
            if ch in CTRL_ASCII:
                raise ValueError('символ %r нельзя использовать в тексте: %r' % (ch, s))
            out.append(o)
        else:
            out += ch.encode('cp932')   # any full-width Japanese char (12px)
    return bytes(out)

def width(s):
    """display width in 6px units"""
    w = 0
    for ch in s:
        if ch == '…': w += 3
        elif ch in '～♪' or ord(ch) > 0x2000 and not (0x400 <= ord(ch) < 0x460): w += 2
        else: w += 1
    return w

FIRST, REST, MAXLINES = 42, 40, 3
def wrap(text):
    """word-wrap Russian text: 42 units on the first line, 40 on the next (engine indents them)."""
    lines = []
    for para in text.split('\n'):
        cur = ''
        for word in para.split(' '):
            lim = FIRST if not lines else REST
            cand = (cur + ' ' + word) if cur else word
            if width(cand) <= lim or not cur:
                cur = cand
            else:
                lines.append(cur); cur = word
        lines.append(cur)
    return lines

def build_fonta(orig):
    d = bytearray(orig)
    for code, hx in GLYPHS.items():
        idx = code - 0x20 if code < 0x80 else code - 0x40
        d[idx*9:idx*9+9] = bytes.fromhex(hx)
    return bytes(d)

# --- untranslated Japanese: half-width kana -> full-width hiragana (stays readable) ---
def _hw_to_fw(chars):
    k = unicodedata.normalize('NFKC', chars)
    out = ''
    for c in k:
        if 'ァ' <= c <= 'ヶ' and c != 'ヴ': c = chr(ord(c) - 0x60)
        out += c
    return out.encode('cp932')

def hw2fw(b):
    out = bytearray(); i = 0
    while i < len(b):
        c = b[i]
        if 0x81 <= c <= 0x9f or 0xe0 <= c <= 0xfc:
            out += b[i:i+2]; i += 2; continue
        if c == 0xa0 and i + 1 < len(b):          # escaped literal
            c = b[i+1]; i += 1
        if 0xa1 <= c <= 0xdf:
            seq = bytes([c]); i += 1
            if i < len(b) and b[i] in (0xde, 0xdf) and c not in (0xde, 0xdf):
                seq += bytes([b[i]]); i += 1
            out += _hw_to_fw(seq.decode('cp932')); continue
        out.append(c); i += 1
    return bytes(out)

# --- control code prefix/suffix of an original line ---
_CTRL = r'(?:[!&@*#/|%:]|[CDQSTWcdqstw](?:,?\d+)(?:,\d+)*)'
PREFIX = re.compile(r'^(?:%s)+' % _CTRL)
SUFFIX = re.compile(r'(?:%s)+$' % r'(?:[CDQSTWcdqstw],?\d+(?:,\d+)*)')
def split_ctrl(jp):
    m = PREFIX.match(jp); pre = m.group() if m else ''
    rest = jp[len(pre):]
    m2 = SUFFIX.search(rest); suf = m2.group() if m2 else ''
    body = rest[:len(rest)-len(suf)] if suf else rest
    return pre, body, suf

# --- English (port of the PSP fan translation) ---------------------------------
from glyphs import GLYPHS_EN
EN_SLOT = {'!': 0x60, ':': 0x5e, '*': 0xbb, '/': 0xbc, '&': 0xbd, '%': 0xbe, '#': 0xbf, '@': 0xdb}
def enc_en(s):
    out = bytearray()
    for ch in s:
        o = ord(ch)
        if ch == '\n': out += b'$'
        elif 'A' <= ch <= 'Z': out.append(0xa1 + o - 65)
        elif 'a' <= ch <= 'z': out.append(0xc0 + o - 97)
        elif ch in EN_SLOT: out.append(EN_SLOT[ch])
        elif ch == '~': out += b'\x81\x60'
        elif ch in '“”': out += b'"'
        elif ch in '‘’': out += b"'"
        elif ch in '—–': out += b'-'
        elif ch == '…': out += b'...'
        elif o < 0x80:
            if ch in CTRL_ASCII: raise ValueError('control char %r in %r' % (ch, s))
            out.append(o)
        else: out += ch.encode('cp932')
    return bytes(out)

def build_fonta_en(orig):
    d = bytearray(orig)
    for code, hx in GLYPHS_EN.items():
        idx = code - 0x20 if code < 0x80 else code - 0x40
        d[idx*9:idx*9+9] = bytes.fromhex(hx)
    return bytes(d)
