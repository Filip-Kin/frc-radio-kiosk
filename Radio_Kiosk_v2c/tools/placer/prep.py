import re,sys,json
s=open(sys.argv[1]).read()
s=re.sub(r'\n\t\(zone\n.*?\n\t\)',lambda m:m.group(0).replace('(clearance 0.1524)','(clearance 0.25)',1),s,flags=re.S)
s=s.replace('\n\t\t(locked yes)','')
s=re.sub(r'(\n\t\((?:segment|via)\n)',r'\1\t\t(locked yes)\n',s)
open(sys.argv[2],'w').write(s)
