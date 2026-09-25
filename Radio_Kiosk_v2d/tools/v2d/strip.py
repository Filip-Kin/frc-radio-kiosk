"""Drop GND from the DSN network: the In1 plane and the pre-placed pad vias carry it."""
import re,sys
t=open(sys.argv[1]).read()
t,k=re.subn(r'\(net\s+"?GND"?\s*\(pins[^()]*(?:\([^()]*\)[^()]*)*\)\s*\)','',t)
open(sys.argv[1],'w').write(t); print('GND stripped',k)
