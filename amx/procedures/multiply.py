#!/usr/bin/python

import re,os,subprocess
from copy import deepcopy
from amx import wordspace
from amx.base.functions import filecopy,resume
from amx.base.gmxwrap import gmx,gmx_run,checkpoint
from amx.base.gromacs import gmxpaths
from amx.base.journal import *
from amx.procedures.common import *

#---multiply is set to follow cgmd_bilayer however this can be changed
from amx.procedures.cgmd_bilayer import command_library
from amx.procedures.cgmd_bilayer import mdp_specs
from amx.procedures.cgmd_bilayer import bilayer_sorter

def multiply(nx=1,ny=1,nz=1,quirky_ions=True,simple=True):

	"""
	Make a copy of a simulation box in multiple directions.
	"""

	factor = nx*ny*nz
	#---update the composition
	#---if the last step doesn't have the composition we step backwards and pick up requirements
	#---note that "protein_ready" is important for the bilayer_sorter 
	for prereq in ['composition','lipids','cation','anion','protein_ready']:
		if prereq not in wordspace:
			steplist = detect_last(steplist=True)[::-1]
			#---walk backwards through steps until we find the commposition
			for ii,i in enumerate(steplist):
				oldspace = resume(read_only=True,step=int(re.match('s([0-9]+)-',i).group(1)))
				if prereq in oldspace:
					wordspace[prereq] = deepcopy(oldspace[prereq])
					break
	#---if composition is available we continue
	wordspace['new_composition'] = [[name,count*factor] for name,count in wordspace['composition']]
	gmx('genconf',structure='system-input',gro='system-multiply',
		nbox="%d %d %d"%(nx,ny,nz),log='genconf-multiply')
	#---reorder the GRO for convenience
	with open(wordspace['step']+'system-multiply.gro') as fp: lines = fp.readlines()
	
	#---collect all unique resiue/atom combinations
	combos = list(set([l[5:15] for l in lines]))

	#---simple method for reordering lines
	if simple:
		#---for each element in the composition, extract all of the residues for that element
		lines_reorder = []
		lines_reorder.extend(lines[:2])
		#---due to ion naming quirks we create a custom keylist
		if quirky_ions:
			keylist = []
			for key,count in wordspace['new_composition']:
				if key in [wordspace[i] for i in ['anion','cation']]:
					keylist.append((('ION',key),slice(5,15),'\s*%s\s*%s\s*'))
				else: keylist.append((key,slice(5,10),'\s*%s\s*'))
		else: keylist = [(i,slice(5,10),'\s*%s\s*') for i in zip(*wordspace['new_composition'])[0]]
		for key,sl,regex in keylist:
			#---! account for ions?
			lines_reorder.extend([l for l in lines[2:-1] if re.match(regex%key,l[sl])])
		lines_reorder.extend([lines[-1]])
		with open(wordspace['step']+'system-multiply-reorder.gro','w') as fp: 
			for line in lines_reorder: fp.write(line)

	#---robust method for reordering lines
	else:

		#---in the following method we will 
		import pdb;pdb.set_trace()
	filecopy(wordspace['step']+'system-multiply-reorder.gro',wordspace['step']+'system.gro')
	wordspace['composition'] = tuple(wordspace['new_composition'])
	del wordspace['new_composition']
