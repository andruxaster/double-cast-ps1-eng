import sys,re
d=open(sys.argv[1],'rb').read()
minlen=int(sys.argv[2]) if len(sys.argv)>2 else 4
pat=re.compile(rb'(?:[\x81-\x9f\xe0-\xef][\x40-\x7e\x80-\xfc]|[\x20-\x7e]){%d,}'%minlen)
for m in pat.finditer(d):
    s=m.group()
    if sum(1 for c in s if c>=0x80)<4: continue
    try: t=s.decode('cp932')
    except: continue
    print('%06x'%m.start(), t)
