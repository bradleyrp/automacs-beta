#!/usr/bin/python

import re,os,subprocess
from amx import wordspace
from amx.base.functions import filecopy
from amx.base.gmxwrap import gmx,gmx_run,checkpoint
from amx.base.gromacs import gmxpaths
from amx.base.journal import *

"""
Atomistic protein simulation module.
"""

#---common command interpretations
command_library = """
pdb2gmx -f STRUCTURE -ff FF -water WATER -o GRO.gro -p system.top -i BASE-posre.itp -missing NONE
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
def component(name,count=None):

	"""
	component(name,count=None)
	Add or modify the composition of the system and return the count if none is provided.
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

def include(name):

	"""
	include(name)
	Add an ITP file to the includes list but avoid redundancies which cause errors in GROMACS.
	"""

	if name not in wordspace['includes']: wordspace['includes'].append(name)

@narrate
def extract_itp(topfile):

	"""
	extract_itp(topfile)
	Extract a `protein.itp` file from a `top` file which is automatically generated by `pdb2gmx`.
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
	#---! needs check for itp list
	wordspace['itp'] = ['protein.itp']

@narrate
def write_top(topfile):

	"""
	write_top(topfile)
	Write the topology file.
	"""

	#---always include forcefield.itp
	if 'includes' not in wordspace: wordspace['includes'] = ['forcefield']		
	with open(wordspace['step']+topfile,'w') as fp:
		#---write include files for the force field
		for incl in wordspace['includes']:
			fp.write('#include "%s.ff/%s.itp"\n'%(wordspace['force_field'],incl))
		#---write include files
		for itp in wordspace['itp']: fp.write('#include "'+itp+'"\n')
		#---write system name
		fp.write('[ system ]\n%s\n\n[ molecules ]\n'%wordspace['system_name'])
		for key,val in wordspace['composition']: fp.write('%s %d\n'%(key,val))

@narrate
def select_minimum(*args,**kwargs):

	"""
	select_minimum(*args,**kwargs)
	Select the structure with the minimum force after consecutive energy minimization steps.
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
def minimize(name,method='steep'):

	"""
	minimize(name,method='steep')
	Standard minimization procedure.
	"""

	gmx('grompp',base='em-%s-%s'%(name,method),top=name,structure=name,
		log='grompp-%s-%s'%(name,method),mdp='input-em-%s-in'%method,skip=True)
	gmx('mdrun',base='em-%s-%s'%(name,method),log='mdrun-%s-%s'%(name,method))
	filecopy(wordspace['step']+'em-'+'%s-%s.gro'%(name,method),
		wordspace['step']+'%s-minimized.gro'%name)
	checkpoint()

	
@narrate
def trim_waters(structure='solvate-dense',gro='solvate',gap=3,boxvecs=None):

	"""
	trim_waters(structure='solvate-dense',gro='solvate',gap=3,boxvecs=None)
	Remove waters within a certain number of Angstroms of the protein.
	"""

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
	with open(wordspace['step']+'script-vmd-trim.tcl','w') as fp:
		for line in vmdtrim: fp.write(line+'\n')
	vmdlog = open(wordspace['step']+'log-script-vmd-trim','w')
	#---previously used os.environ['VMDNOCUDA'] = "1" but this was causing segfaults on green
	p = subprocess.Popen('VMDNOCUDA=1 '+gmxpaths['vmd']+' -dispdev text -e script-vmd-trim.tcl',
		stdout=vmdlog,stderr=vmdlog,cwd=wordspace['step'],shell=True)
	p.communicate()
	with open(wordspace['bash_log'],'a') as fp:
		fp.write(gmxpaths['vmd']+' -dispdev text -e script-vmd-trim.tcl &> log-script-vmd-trim\n')
	#---! need to add VMD script to the BASH script here
	gmx_run(gmxpaths['editconf']+' -f solvate-vmd.pdb -o solvate.gro -resnr 1',
		log='editconf-convert-vmd')

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
	component('SOL',count=nwaters)
	include(wordspace['water'])
	write_top('solvate.top')

@narrate
def counterions(structure,top):

	"""
	counterions(structure,top)
	Standard procedure for adding counterions.
	"""

	filecopy(wordspace['step']+top+'.top',wordspace['step']+'counterions.top')
	gmx('grompp',base='genion',structure=structure,
		top='counterions',mdp='input-em-steep-in',
		log='grompp-genion')
	gmx('make_ndx',structure=structure,ndx='solvate-waters',
		inpipe='keep 0\nr SOL\nkeep 1\nq\n',
		log='make-ndx-counterions-check')
	gmx('genion',base='genion',gro='counterions',ndx='solvate-waters',
		cation=wordspace['cation'],anion=wordspace['anion'],
		flag='-conc %f -neutral'%wordspace['ionic_strength'],
		log='genion')
	with open(wordspace['step']+'log-genion','r') as fp: lines = fp.readlines()
	declare_ions = filter(lambda x:re.search('Will try',x)!=None,lines).pop()
	ion_counts = re.findall(
		'^Will try to add ([0-9]+) (\w+) ions and ([0-9]+) (\w+) ions',declare_ions).pop()
	for ii in range(2): component(ion_counts[2*ii+1],count=ion_counts[2*ii])
	component('SOL',count=component('SOL')-component(ion_counts[1])-component(ion_counts[3]))
	include('ions')
	write_top('counterions.top')

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

@narrate
def equilibrate():

	"""
	equilibrate()
	Standard minimization procedure.
	"""

	#---sequential equilibration stages
	seq = wordspace['equilibration'].split(',')
	for eqnum,name in enumerate(seq):
		gmx('grompp',base='md-%s'%name,top='system',
			structure='system' if eqnum == 0 else 'md-%s'%seq[eqnum-1],
			log='grompp-%s'%name,mdp='input-md-%s-eq-in'%name)
		gmx('mdrun',base='md-%s'%name,log='mdrun-%s'%name,skip=True)
		checkpoint()

	#---first part of the equilibration/production run
	gmx('grompp',base='md.part0001',top='system',
		structure='md-%s'%seq[-1],
		log='grompp-0001',mdp='input-md-in')
	gmx('mdrun',base='md.part0001',log='mdrun-0001')
	checkpoint()
	
