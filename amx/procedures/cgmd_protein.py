#!/usr/bin/python

from amx import wordspace
from amx.base.gmxwrap import bash,gmx_run
from amx.base.gromacs import gmxpaths
from amx.base.journal import *

#---common command interpretations
command_library = """"""
mdp_specs = {}

def build_cgmd_protein():

	"""
	Use martinize to generate a coarse-grained protein.
	"""

	name = 'protein'
	cwd = wordspace['step']
	martinize_fn = os.path.expanduser(wordspace['martinize_path'])
	#---this function is run from the step but martinize_path is relative to root
	assert os.path.isfile(martinize_fn)
	cmd = 'python '+martinize_fn+' -v -p backbone '
	cmd += ' -f protein-start.pdb -o %s.top -x %s.pdb'%(name,name)
	if 'dssp' in wordspace: cmd += ' -dssp %s'%os.path.abspath(os.path.expanduser(wordspace['dssp']))
	if 'martinize_ff' in wordspace: cmd += ' -ff %s'%wordspace['martinize_ff']
	if 'martinize_flags' in wordspace: cmd += ' '+wordspace['martinize_flags']
	bash(cmd,cwd=wordspace['step'],log='martinize')
	assert os.path.isfile(wordspace['step']+'protein.pdb')
	gmx_run(gmxpaths['editconf']+' -f %s.pdb -o %s.gro'%(name,name),log='editconf-convert-pdb')
	#---only allow Z-restraints because this is probably for a bilayer
	bash("sed -i 's/POSRES_FC    POSRES_FC    POSRES_FC/0 0 POSRES_FC/g' Protein.itp",
		cwd=wordspace['step'])
