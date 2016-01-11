#!/usr/bin/python -i
execfile('/etc/pythonstart')

settings = """
system_name:        CGMD BILAYER
lipid_structures:   inputs/cgmd-lipid-structures
step:               bilayer
procedure:          cgmd,bilayer
shape:              flat
lx:                 100
ly:                 100
lz:                 50
height:             6
binsize:            0.9
monolayer_offset:   1.5
lipid:              DOPC
"""

import amx
amx.init(settings)
amx.start(amx.wordspace['step'])
amx.build_bilayer(name='vacuum-bilayer.gro')
amx.filecopy(amx.wordspace['last']+amx.wordspace['protein_ready'],amx.wordspace['step'])
amx.filecopy(amx.wordspace['last']+amx.wordspace['lipid_ready'],amx.wordspace['step'])
amx.gro_combinator('vacuum-bilayer.gro',amx.wordspace['protein_ready'],
	amx.wordspace['lipid_ready'],cwd=amx.wordspace['step'])
if 'protein_ready' in amx.wordspace:
	amx.adhere_protein_cgmd_bilayer(bilayer='vacuum-bilayer.gro',combo='combo.gro')
