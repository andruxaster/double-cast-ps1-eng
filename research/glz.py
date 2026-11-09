def decode(src, pos, outsize):
    out=bytearray(); flags=0
    def nb():
        nonlocal pos
        b=src[pos]; pos+=1; return b
    def bit():
        nonlocal flags
        flags>>=1
        if not (flags & 0x7f00): flags=nb()|0xff00
        return flags&1
    while len(out)<outsize:
        if bit():
            if bit():
                b1=nb(); b2=nb()
                off=b1+1+((b2&0xf)<<8)
                n=b2>>4
                n = n+2 if n else nb()+0x12
                s=len(out)-off
                for i in range(n): out.append(out[s+i])
            else:
                n=nb()+0xb
                for i in range(n): out.append(nb())
        else:
            out.append(nb())
    return bytes(out), pos
