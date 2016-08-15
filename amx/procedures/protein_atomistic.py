#!/usr/bin/python

import re,os,subprocess
from amx import wordspace
from amx.base.functions import filecopy
from amx.base.gmxwrap import gmx,gmx_run,checkpoint
from amx.base.gromacs import gmxpaths
from amx.base.journal import *
from amx.procedures.common import *

"""
Atomistic protein simulation module.
"""

#---common command interpretations
command_library = """
pdb2gmx -f STRUCTURE -ff FF -water WATER -o GRO.gro -p system.top -i BASE-posre.itp -missing NONE -ignh NONE
editconf -f STRUCTURE.gro -o GRO.gro
grompp -f MDP.mdp -c STRUCTURE.gro -p TOP.top -o BASE.tpr -po BASE.mdp
mdrun -s BASE.tpr -cpo BASE.cpt -o BASE.trr -x BASE.xtc -e BASE.edr -g BASE.log -c BASE.gro -v NONE
genbox -cp STRUCTURE.gro -cs SOLVENT.gro -o GRO.gro
make_ndx -f STRUCTURE.gro -o NDX.ndx
genion -s BASE.tpr -o GRO.gro -n NDX.ndx -nname ANION -pname CATION
trjconv -f STRUCTURE.gro -n NDX.ndx -center NONE -s TPR.tpr -o GRO.gro
"""

#---customized parameters
mdp_specs = {
	'group':'aamd',
	'input-em-steep-in.mdp':['minimize'],
	'input-em-cg-in.mdp':['minimize',{'integrator':'cg'}],
	'input-md-nvt-eq-in.mdp':['nvt-protein'],
	'input-md-nvt-short-eq-in.mdp':['nvt-protein-short'],
	'input-md-npt-eq-in.mdp':['npt-protein'],
	'input-md-in.mdp':None,
	}

#---FUNCTIONS
#-------------------------------------------------------------------------------------------------------------

@narrate
def extract_itp(topfile):

	"""
	extract_itp(topfile)
	Extract a `protein.itp` file from a `top` file which is automatically generated by `pdb2gmx`.
	Note that parts of this function was poached to read_top in common.
	"""

	with open(wordspace['step']+topfile,'r') as f: topfile = f.read()
	chains = {}
	startline = [ii for ii,i in enumerate(topfile.split('\n')) 
		if re.match('^(\s+)?\[(\s+)?molecules(\s+)?\]',i)][0]
	count_regex = '^(\w+)\s+([0-9]+)'
	components = [re.findall(count_regex,line).pop()
		for line in topfile.split('\n')[startline:] if re.match(count_regex,line)]		
	for name,count in components: component(name,count=int(count))
	with open(wordspace['step']+'protein.itp','w') as fp: 
		for line in topfile.split('\n'):
			#---skip any part of the top that follows the water topology and/or system composition
			if re.match('; Include water topology',line): break
			if re.match('; Include topology for ions',line): break
			if re.match('\[ system \]',line): break
			#---you must extract forcefield.itp from the file to prevent redundant includes
			if not re.match(".+forcefield\.itp",line) and not \
				re.match("; Include forcefield parameters",line): 
				fp.write(line+'\n')
	if 'itp' not in wordspace: wordspace['itp'] = ['protein.itp']
	else: wordspace.itp.append('protein.itp')

@narrate
def select_minimum(*args,**kwargs):

	"""
	select_minimum(*args,**kwargs)
	Select the structure with the minimum force after consecutive energy minimization steps.
	MOVED TO COMMON
	"""

	gro = 'confout' if 'gro' not in kwargs else kwargs['gro']
	forces = {}
	for arg in args:
		#---! naming rule is applied here
		with open(wordspace['step']+'log-mdrun-'+arg,'r') as fp: lines = fp.readlines()
		finished = filter(lambda x: re.match('^Maximum (f|F)orce',x),lines)
		if finished != []:
			forces[arg] = float(re.findall('^[^=]+=\s*([^\s]+)',
				filter(lambda x: re.match('^Maximum (f|F)orce',x),lines).pop()).pop())
	if len(forces)==1: arg = forces.keys()[0]
	else: arg = filter(lambda x: forces[x]==min(forces.values()),forces.keys())[0]
	filecopy(wordspace['step']+'em-'+arg+'.gro',wordspace['step']+gro+'.gro')

@narrate
def minimize_steep_cg(name):

	"""
	minimize_steep_cg(name)
	Minimization using steepest descent followed by conjugate gradient.
	Note that this method has been retired due to reliability issues.
	"""

	gmx('grompp',base='em-%s-steep'%name,top=name,structure=name,
		log='grompp-em-%s-steep'%name,mdp='input-em-steep-in')
	gmx('mdrun',base='em-%s-steep'%name,log='mdrun-%s-steep'%name,skip=True)
	#---if first step fails we skip it and try again with the second minimizer
	if not os.path.isfile(wordspace['step']+'em-%s-steep.gro'):
		filecopy(wordspace['step']+'%s.gro'%name,wordspace['step']+'em-%s-steep.gro'%name)
	gmx('grompp',base='em-%s-cg'%name,top=name,structure='em-%s-steep'%name,
		log='grompp-%s-cg'%name,mdp='input-em-cg-in',skip=True)
	gmx('mdrun',base='em-%s-cg'%name,log='mdrun-%s-cg'%name)
	select_minimum('%s-steep'%name,'%s-cg'%name,gro='%s-minimized'%name)
	checkpoint()

@narrate
def solvate(structure,top):

	"""
	solvate(structure,top)
	Standard solvate procedure for atomistic protein in water.
	"""
	
	#---purge the wordspace of solvent and anions in case we are resuming
	for key in [wordspace['anion'],wordspace['cation'],'SOL']:
		if key in zip(*wordspace['composition'])[0]:
			del wordspace['composition'][zip(*wordspace['composition'])[0].index(key)]
	gmx('editconf',structure=structure,gro='solvate-box-alone',
		log='editconf-checksize',flag='-d 0')
	with open(wordspace['step']+'log-editconf-checksize','r') as fp: lines = fp.readlines()
	boxdims = map(lambda y:float(y),re.findall('\s*box vectors \:\s*([^\s]+)\s+([^\s]+)\s+([^\s]+)',
		filter(lambda x:re.match('\s*box vectors',x),lines).pop()).pop())
	boxvecs = tuple([i+2*wordspace['water_buffer'] for i in boxdims])
	center = tuple([i/2. for i in boxvecs])
	#---cube is not implemented yet
	gmx('editconf',structure=structure,gro='solvate-protein',
		flags='-center %f %f %f'%center+' '+'-box %f %f %f'%boxvecs,
		log='editconf-center-protein')
	gmx('genbox',structure='solvate-protein',solvent=wordspace['solvent'],
		gro='solvate-dense',#top='solvate-standard',
		log='genbox-solvate')
	#---trim waters if the protein_water_gap setting is not False
	if 'protein_water_gap' in wordspace and wordspace['protein_water_gap'] != False:
		trim_waters(structure='solvate-dense',gro='solvate',
			gap=wordspace['protein_water_gap'],boxvecs=boxvecs)
	else: filecopy(wordspace['step']+'solvate-dense.gro',wordspace['step']+'solvate.gro')
	gmx('make_ndx',structure='solvate',ndx='solvate-water-check',inpipe='q\n',
		log='make-ndx-solvate-check')
	with open(wordspace['step']+'log-make-ndx-solvate-check','r') as fp: lines = fp.readlines()
	nwaters = int(re.findall('\s*[0-9]+\s+Water\s+:\s+([0-9]+)\s+atoms',
		filter(lambda x:re.match('\s*[0-9]+\s+Water',x),lines).pop()).pop())/3
	wordspace['water_without_ions'] = nwaters
	component('SOL',count=nwaters)
	#---add the suffix so that water is referred to by its name in the settings
	include(wordspace['water'],ff=True)
	write_top('solvate.top')

@narrate
def write_structure_pdb(structure,pdb):

	"""
	write_structure_pdb(structure,pdb)
	Infer the starting residue from the original PDB and write structure.pdb with the correct indices
	according to the latest GRO structure (typically counterions.gro).
	"""

	#---automatically center the protein in the box here and write the final structure
	gmx('make_ndx',structure='counterions',ndx='counterions-groups',
		log='make-ndx-counterions',inpipe='q\n',)
	with open(wordspace['step']+'log-make-ndx-counterions','r') as fp: lines = fp.readlines()
	relevant = [filter(lambda x:re.match('\s*[0-9]+\s+%s'%name,x),lines) for name in ['System','Protein']]
	groupdict = dict([(j[1],int(j[0])) for j in 
		[re.findall('^\s*([0-9]+)\s(\w+)',x[0])[0] for x in relevant]])
	gmx('trjconv',ndx='counterions-groups',structure='counterions-minimized',
		inpipe='%d\n%d\n'%(groupdict['Protein'],groupdict['System']),
		log='trjconv-counterions-center',tpr='em-counterions-steep',gro='system')
	with open(wordspace['step']+pdb,'r') as fp: lines = fp.readlines()
	startres = int([line for line in lines if re.match('^ATOM',line)][0][23:26+1])
	gmx('editconf',structure=structure,
		flag='-o structure.pdb -resnr %d'%startres,
		log='editconf-structure-pdb')

