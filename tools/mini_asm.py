# Minimal MIPS (R3000) assembler for small engine hooks.
import re, struct
REG = {n: i for i, n in enumerate('zero at v0 v1 a0 a1 a2 a3 t0 t1 t2 t3 t4 t5 t6 t7 s0 s1 s2 s3 s4 s5 s6 s7 t8 t9 k0 k1 gp sp fp ra'.split())}
def r(x): return REG[x.strip().lstrip('$')]
def imm(x): return int(x, 0) & 0xffff
I = {'addiu': 9, 'andi': 12, 'sltiu': 11, 'slti': 10, 'ori': 13, 'lui': 15}
M = {'lb': 0x20, 'lh': 0x21, 'lw': 0x23, 'lbu': 0x24, 'lhu': 0x25, 'sb': 0x28, 'sh': 0x29, 'sw': 0x2b}
def assemble(src, base):
    lines = []
    for ln in src.strip().splitlines():
        ln = ln.split('#')[0].strip()
        if ln: lines.append(ln)
    labels = {}; addr = base; insts = []
    for ln in lines:
        if ln.endswith(':'): labels[ln[:-1]] = addr; continue
        insts.append((addr, ln)); addr += 4
    out = b''
    def tgt(x): return labels[x] if x in labels else int(x, 0)
    for a, ln in insts:
        op, _, rest = ln.partition(' '); args = [s.strip() for s in rest.split(',')] if rest else []
        if op == 'nop': w = 0
        elif op == 'move': w = (r(args[1]) << 21) | (r(args[0]) << 11) | 0x21
        elif op == 'slt': w = (r(args[1]) << 21) | (r(args[2]) << 16) | (r(args[0]) << 11) | 0x2a
        elif op in I: w = (I[op] << 26) | (r(args[1]) << 21) | (r(args[0]) << 16) | imm(args[2])
        elif op in M:
            m = re.match(r'(.+)\((.+)\)', args[1]); w = (M[op] << 26) | (r(m.group(2)) << 21) | (r(args[0]) << 16) | imm(m.group(1))
        elif op in ('beq', 'bne', 'b'):
            if op == 'b': op, args = 'beq', ['zero', 'zero', args[0]]
            off = (tgt(args[2]) - (a + 4)) >> 2
            w = ((4 if op == 'beq' else 5) << 26) | (r(args[0]) << 21) | (r(args[1]) << 16) | (off & 0xffff)
        elif op in ('j', 'jal'): w = ((2 if op == 'j' else 3) << 26) | ((tgt(args[0]) >> 2) & 0x3ffffff)
        else: raise ValueError(ln)
        out += struct.pack('<I', w)
    return out
