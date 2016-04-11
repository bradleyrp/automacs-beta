#!/usr/bin/python

import re,os,subprocess
from amx import wordspace
from amx.base.functions import filecopy
from amx.base.gmxwrap import gmx,gmx_run,checkpoint
from amx.base.gromacs import gmxpaths
from amx.base.journal import *
from amx.procedures.common import *
import numpy as np

command_library = """
grompp -f MDP.mdp -c STRUCTURE.gro -p TOP.top -o BASE.tpr -po BASE.mdp
mdrun -s BASE.tpr -cpo BASE.cpt -o BASE.trr -x BASE.xtc -e BASE.edr -g BASE.log -c BASE.gro -v NONE
"""
mdp_specs = ""

@narrate
def read_topology(top):

	"""
	See what's in the system.
	"""

	with open(wordspace['step']+top) as fp: lines = fp.readlines()
	molecules_lineno, = [ii for ii,i in enumerate(lines) if re.search('\[\s*molecules\s*\]',i)]
	component_regex = '^\s*(\w+)\s+([0-9]+)'
	for line in lines[molecules_lineno+1:]:
		if re.match(component_regex,line):
			name,number = re.findall(component_regex,line)[0]
			component(name,count=number)

@narrate
def estimate_concentrations(structure):

	"""
	Use genion to estimate the current concentration?
	"""

	with open(wordspace['step']+structure) as fp: lines = fp.readlines()
	box = [float(i) for i in lines[-1].split()]
	ion_counts = {key:val for key,val in wordspace['composition'] if key in wordspace['all_ion_names']}
	volume = np.product(box)
	for key,val in ion_counts.items(): report('concentration of %s is %f'%(key,val/volume),'note')
	report('total ionic concentration is %f'%(sum([val for val in ion_counts.values()])/volume),'note')
	#---! better way to save these data or at least port this code for doing concentrations across sims

def identify_candidate_replacements(structure,gro,top):

	"""
	Historical development note:
	The reionize code was designed to perform some tests on a lipid-ion dataset. 
	For expedience, we only perform the custom reionization desired here.
	"""

	#---read the structure
	points,atom_names,lines = read_gro(structure)
	#---read the topology
	read_top(wordspace.step+top)
		
	procedures = wordspace.reionize_specify.keys()
	for procedure in procedures:
		if procedure == 'some_divalents':

			"""
			In this procedure we find some ions that are in the center of the water (and hence away from the
			bilayer if one exists) and replace them with another ion.
			"""

			#---internal loop over which ions to change into which other ions (in case you want multiple)
			for key,val in wordspace.reionize_specify['some_divalents'].items():
				transformed = key
				targets = val['from']
				quantity = val['quantity']
				#---locate all ions
				candidates_for_replace = list(np.where(atom_names==targets)[0])
				#---! currently choosing a random subset of these to replace
				import random
				remove_quantity = quantity+(val['also_delete'] if 'also_delete' in val else 0)
				disappear = sorted(random.sample(candidates_for_replace,remove_quantity))
				#---change ion types here and write the new structure
				for change in disappear[:quantity]:
					line = list(lines[2+change])
					#---here we use the name-name convention instead of the "ION" residue name
					line[5:10] = transformed.ljust(5)
					line[10:15] = transformed.rjust(5)
					lines[2+change] = ''.join(line)
					#---copy the line to the end
					lines.insert(-1,lines[2+change])
				for change in disappear[::-1]: lines.pop(2+change)
				component(targets,count=component(targets)-remove_quantity)
				component(transformed,count=quantity)
				#---in case we have fewer total atoms in the system we update the count here
				lines[1] = '%s\n'%(len(lines)-3)
		else: raise Exception('cannot understand reionize_procedure: %s in reionize_specify'%procedure)
	#---write the structure
	with open(wordspace.step+gro+'.gro','w') as fp: fp.write(''.join(lines))
	shutil.move(wordspace.step+top,wordspace.step+'system.old.top')
	write_top(top)
