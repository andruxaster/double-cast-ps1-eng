import unicodedata
def dec(b):
    out=[];i=0
    while i<len(b):
        c=b[i]
        if (0x81<=c<=0x9f or 0xe0<=c<=0xfc) and i+1<len(b):
            try: out.append(b[i:i+2].decode('cp932'))
            except: out.append('<%02x%02x>'%(c,b[i+1]))
            i+=2; continue
        if 0xa1<=c<=0xdf:
            k=bytes([c]).decode('cp932')
            k=unicodedata.normalize('NFKC',k)
            # katakana->hiragana
            if 'ァ'<=k<='ヶ': k=chr(ord(k)-0x60)
            out.append(k)
        elif 0x20<=c<0x7f: out.append(chr(c))
        else: out.append('<%02x>'%c)
        i+=1
    s=''.join(out)
    return unicodedata.normalize('NFC',s.replace('゛','゙').replace('゜','゚'))
