#!/usr/bin/python

import re,os,subprocess
from amx import wordspace
from amx.base.functions import filecopy
from amx.base.gmxwrap import gmx,gmx_run,checkpoint
from amx.base.gromacs import gmxpaths
from amx.base.journal import *

"""
Common simulation construction tools.
"""

@narrate
def component(name,count=None):

	"""
	component(name,count=None)
	Add or modify the composition of the system and return the count if none is provided.
	Originally designed for protein_atomistic.py.
	"""
	
	#---start a composition list if absent
	if 'composition' not in wordspace: 
		wordspace['composition'] = []
		try: wordspace['composition'].append([name,int(count)])
		except: raise Exception('[ERROR] the first time you add a component you must supply a count')
	#---if count is supplied then we change the composition
	names = zip(*wordspace['composition'])[0]
	if count != None:
		if name in names: wordspace['composition'][names.index(name)][1] = int(count)
		else: wordspace['composition'].append([name,int(count)])
	#---return the requested composition
	names = zip(*wordspace['composition'])[0]
	return wordspace['composition'][names.index(name)][1]

@narrate
def get_box_vectors(structure,gro=None,d=0,log='checksize'):

	"""
	Return the box vectors.
	"""

	if not gro: gro = structure+'-gro'
	#---note that we consult the command_library here
	gmx('editconf',structure=structure,gro=gro,
		log='editconf-%s'%log,flag='-d %d'%d)
	with open(wordspace['step']+'log-editconf-%s'%log,'r') as fp: lines = fp.readlines()
	box_vector_regex = '\s*box vectors\s*\:\s*([^\s]+)\s+([^\s]+)\s+([^\s]+)'
	box_vector_new_regex = '\s*new box vectors\s*\:\s*([^\s]+)\s+([^\s]+)\s+([^\s]+)'
	return [[[float(j) for j in re.findall(regex,line)[0]] 
		for line in lines if re.match(regex,line)][0] 
		for regex in [box_vector_regex,box_vector_new_regex]]

@narrate
def count_molecules(structure,resname):

	"""
	Count the number of molecules in a system using make_ndx.
	"""

	gmx('make_ndx',structure=structure,ndx=structure+'-count',
		log='make-ndx-%s-check'%structure,inpipe='q\n')
	with open(wordspace['step']+'log-make-ndx-%s-check'%structure) as fp: lines = fp.readlines()
	residue_regex = '^\s*[0-9]+\s+%s\s+\:\s([0-9]+)\s'%resname
	count, = [int(re.findall(residue_regex,l)[0]) for l in lines if re.match(residue_regex,l)]
	return count
	
@narrate
def trim_waters(structure='solvate-dense',gro='solvate',gap=3,boxvecs=None,method='aamd'):

	"""
	trim_waters(structure='solvate-dense',gro='solvate',gap=3,boxvecs=None)
	Remove waters within a certain number of Angstroms of the protein.
	"""

	if gap != 0.0:
		if method == 'aamd':
			vmdtrim = [
				'package require pbctools',
				'mol new solvate-dense.gro',
				'set sel [atomselect top \"(all not ('+\
				'water and (same residue as water within '+str(gap)+\
				' of not water)'+\
				')) and '+\
				'same residue as (x>=0 and x<='+str(10*boxvecs[0])+\
				' and y>=0 and y<= '+str(10*boxvecs[1])+\
				' and z>=0 and z<= '+str(10*boxvecs[2])+')"]',
				'$sel writepdb solvate-vmd.pdb',
				'exit',]			
		elif method == 'cgmd':
			vmdtrim = [
				'package require pbctools',
				'mol new solvate-dense.gro',
				'set sel [atomselect top \"(all not ('+\
				'resname W and (same residue as resname W and within '+str(gap)+\
				' of not resname W)'+\
				')) and '+\
				'same residue as (x>=0 and x<='+str(10*boxvecs[0])+\
				' and y>=0 and y<= '+str(10*boxvecs[1])+\
				' and z>=0 and z<= '+str(10*boxvecs[2])+')"]',
				'$sel writepdb solvate-vmd.pdb',
				'exit',]			
		with open(wordspace['step']+'script-vmd-trim.tcl','w') as fp:
			for line in vmdtrim: fp.write(line+'\n')
		vmdlog = open(wordspace['step']+'log-script-vmd-trim','w')
		#---previously used os.environ['VMDNOCUDA'] = "1" but this was causing segfaults on green
		p = subprocess.Popen('VMDNOCUDA=1 '+gmxpaths['vmd']+' -dispdev text -e script-vmd-trim.tcl',
			stdout=vmdlog,stderr=vmdlog,cwd=wordspace['step'],shell=True,executable='/bin/bash')
		p.communicate()
		with open(wordspace['bash_log'],'a') as fp:
			fp.write(gmxpaths['vmd']+' -dispdev text -e script-vmd-trim.tcl &> log-script-vmd-trim\n')
		gmx_run(gmxpaths['editconf']+' -f solvate-vmd.pdb -o solvate.gro -resnr 1',
			log='editconf-convert-vmd')
	else: filecopy(wordspace['step']+'solvate-dense.gro',wordspace['step']+'solvate.gro')