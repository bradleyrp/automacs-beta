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

def multiply(nx=1,ny=1,nz=1,quirky_ions=True):

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
	kwargs = {}
	if type(wordspace['genconf_gap'])!=list: gap = [wordspace.genconf_gap for i in range(3)]
	else: gap = wordspace['genconf_gap']
	if 'buffer' in wordspace: kwargs['flag'] = ' -dist %.2f %.2f %.2f'%tuple(gap)
	gmx('genconf',structure='system-input',gro='system-multiply',
		nbox="%d %d %d"%(nx,ny,nz),log='genconf-multiply',**kwargs)
	#---copy ITP files
	for itp in wordspace.itp:
		filecopy(wordspace.last_step+itp,wordspace.step+itp)
	#---reorder the GRO for convenience
	with open(wordspace['step']+'system-multiply.gro') as fp: lines = fp.readlines()
	#---collect all unique resiue/atom combinations
	combos = list(set([l[5:15] for l in lines]))

	#---for each element in the composition, extract all of the residues for that element
	lines_reorder = []
	lines_reorder.extend(lines[:2])
	#---develop a list of filtering rules
	keylist = {}
	for key,count in wordspace['new_composition']:
		if key in [wordspace[i] for i in ['anion','cation']]:
			keylist[key] = 'regex',(('ION',key),slice(5,15),'\s*%s\s*%s\s*')
		elif re.match('^(p|P)rotein',key) and key+'.itp' in wordspace.itp:
			#---custom procedure for finding proteins which have variegated residue numbers
			itp = read_itp(wordspace.step+key+'.itp')
			residues_starts = []
			seq = list(zip(*itp['atoms'])[3])
			residues = [i[5:10].strip() for i in lines]
			for i in range(len(residues)-len(seq)):
				#---minor speed up by checking the first one
				if seq[0]==residues[i] and residues[i:i+len(seq)]==seq: 
					residues_starts.append(i)
			keylist[key] = 'slices',[slice(i,i+len(seq)) for i in residues_starts]
		else: keylist[key] = 'regex',(key,slice(5,10),'\s*%s\s*')
	for key,count in wordspace['new_composition']:
		method,details = keylist[key]
		if method == 'regex':
			key,sl,regex = details
			lines_reorder.extend([l for l in lines[2:-1] if re.match(regex%key,l[sl])])	
		elif method == 'slices':
			for sl in details: lines_reorder.extend(lines[sl])	
		else: raise
	lines_reorder.extend([lines[-1]])
	with open(wordspace['step']+'system-multiply-reorder.gro','w') as fp: 
		for line in lines_reorder: fp.write(line)

	filecopy(wordspace['step']+'system-multiply-reorder.gro',wordspace['step']+'system.gro')
	wordspace['composition'] = tuple(wordspace['new_composition'])
	del wordspace['new_composition']
