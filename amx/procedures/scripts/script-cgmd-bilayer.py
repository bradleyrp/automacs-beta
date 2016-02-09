#!/usr/bin/python -i
execfile('/etc/pythonstart')

settings = """
step:               bilayer
system_name:        CGMD BILAYER
lipid_structures:   inputs/cgmd-lipid-structures
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

from amx import *
init(settings)
start(wordspace['step'])
build_bilayer(name='vacuum-bilayer.gro')
filecopy(wordspace['last']+wordspace['protein_ready'],wordspace['step'])
filecopy(wordspace['last']+wordspace['lipid_ready'],wordspace['step'])
if 'protein_ready' in wordspace:
	gro_combinator(wordspace['protein_ready'],
		wordspace['lipid_ready'],cwd=wordspace['step'],out='protein-lipid.gro')
	adhere_protein_cgmd_bilayer(bilayer='vacuum-bilayer.gro',
		protein_complex='protein-lipid.gro',combo='vacuum.gro')
#---! needs generalized
os.system('cp -arv inputs/martini.ff '+wordspace['step'])
filecopy('inputs/PIP2.itp',wordspace['step'])
filecopy(wordspace['last']+"Protein.itp",wordspace['step'])
wordspace['itp'] = ['Protein.itp','PIP2.itp']
wordspace['ff_includes'] = eval(wordspace['ff_includes'])
wordspace['composition'] = [
	(wordspace['lipid'],
		int(wordspace['lx']/wordspace['binsize'])*int(wordspace['ly']/wordspace['binsize'])*2),
	('Protein',1),
	('PIP2',1)]
write_top('vacuum.top')
write_mdp()
minimize('vacuum',method='steep')
import pickle
pickle.dump(wordspace,open('wordspace.pkl','w'))

"""
"""