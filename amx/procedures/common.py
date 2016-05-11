#!/usr/bin/python

import re,os,subprocess
from amx import wordspace
from amx.base.functions import filecopy
from amx.base.gmxwrap import gmx,gmx_run,checkpoint
from amx.base.gromacs import gmxpaths
from amx.base.journal import narrate,report
from amx.base.tools import detect_last
import shutil,glob

"""
Common simulation construction tools.
"""

@narrate
def component(name,count=None,top=False):

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
		else: 
			if top: wordspace['composition'].insert(0,[name,int(count)])
			else: wordspace['composition'].append([name,int(count)])
	#---return the requested composition
	names = zip(*wordspace['composition'])[0]
	return wordspace['composition'][names.index(name)][1]

@narrate
def get_box_vectors(structure,gro=None,d=0,log='checksize'):

	"""
	Return the box vectors.
	"""

	if not gro: gro = structure+'-check-box'
	#---note that we consult the command_library here
	gmx('editconf',structure=structure,gro=gro,
		log='editconf-%s'%log,flag='-d %d'%d)
	with open(wordspace['step']+'log-editconf-%s'%log,'r') as fp: lines = fp.readlines()
	box_vector_regex = '\s*box vectors\s*\:\s*([^\s]+)\s+([^\s]+)\s+([^\s]+)'
	box_vector_new_regex = '\s*new box vectors\s*\:\s*([^\s]+)\s+([^\s]+)\s+([^\s]+)'
	runon_regex = '^\s*([0-9]+\.?[0-9]{0,3})\s*([0-9]+\.?[0-9]{0,3})\s*([0-9]+\.?[0-9]{0,3})'
	old_line = [l for l in lines if re.match(box_vector_regex,l)][0]
	vecs_old = re.findall('\s*box vectors\s*:([^\(]+)',old_line)[0]
	#---sometimes the numbers run together
	try: vecs_old = [float(i) for i in vecs_old.strip(' ').split()]
	except: vecs_old = [float(i) for i in re.findall(runon_regex,vecs_old)[0]]
	#---repeat for new box vectors
	new_line = [l for l in lines if re.match(box_vector_new_regex,l)][0]
	vecs_new = re.findall('\s*box vectors\s*:([^\(]+)',new_line)[0]
	try: vecs_new = [float(i) for i in vecs_new.strip(' ').split()]
	except: vecs_new = [float(i) for i in re.findall(runon_regex,vecs_new)[0]]
	#---no need to keep the output since it is a verbatim copy for diagnostic only
	os.remove(wordspace['step']+gro+'.gro')
	#import pdb;pdb.set_trace()
	return vecs_old,vecs_new

@narrate
def count_molecules(structure,resname):

	"""
	Count the number of molecules in a system using make_ndx.
	"""

	gmx('make_ndx',structure=structure,ndx=structure+'-count',
		log='make-ndx-%s-check'%structure,inpipe='q\n')
	with open(wordspace['step']+'log-make-ndx-%s-check'%structure) as fp: lines = fp.readlines()
	residue_regex = '^\s*[0-9]+\s+%s\s+\:\s+([0-9]+)\s'%resname
	count, = [int(re.findall(residue_regex,l)[0]) for l in lines if re.match(residue_regex,l)]
	return count
	
@narrate
def trim_waters(structure='solvate-dense',gro='solvate',
	gap=3,boxvecs=None,method='aamd',boxcut=True,use_vmd=False):

	"""
	trim_waters(structure='solvate-dense',gro='solvate',gap=3,boxvecs=None)
	Remove waters within a certain number of Angstroms of the protein.
	"""

	if gap != 0.0 and use_vmd:
		if method == 'aamd': watersel = "water"
		elif method == 'cgmd': watersel = "resname W"
		else: raise Exception("\n[ERROR] unclear method %s"%method)
		if 'sol' in wordspace: watersel = "resname %s"%wordspace.sol
		vmdtrim = [
			'package require pbctools',
			'mol new %s.gro'%structure,
			'set sel [atomselect top \"(all not ('+\
			'%s and (same residue as %s and within '%(watersel,watersel)+str(gap)+\
			' of not %s)))'%watersel]
		#---box trimming is typical for e.g. atomstic protein simulations but discards anything outside
		if boxcut:
			vmdtrim += [' and '+\
			'same residue as (x>=0 and x<='+str(10*boxvecs[0])+\
			' and y>=0 and y<= '+str(10*boxvecs[1])+\
			' and z>=0 and z<= '+str(10*boxvecs[2])+')']
		vmdtrim += ['"]','$sel writepdb solvate-vmd.pdb','exit',]			
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
	#---scipy is more reliable than VMD
	elif gap != 0.0:
		import scipy
		import scipy.spatial
		import numpy as np
		#---if "sol" is not in the wordspace we assume this is atomistic and use the standard "SOL"
		watersel = wordspace.get('sol','SOL')
		incoming = read_gro(structure+'.gro')
		#---remove waters that are near not-waters
		is_water = np.array(incoming['residue_names'])==watersel
		is_not_water = np.array(incoming['residue_names'])!=watersel
		water_inds = np.where(is_water)[0]
		not_water_inds = np.where(np.array(incoming['residue_names'])!=watersel)[0]
		points = np.array(incoming['points'])
		dists = scipy.spatial.distance.cdist(points[water_inds],points[not_water_inds])
		residue_indices = np.array(incoming['residue_indices'])
		#---list of residue indices in is_water that have at least one atom with an overlap
		excludes = np.array(incoming['residue_indices'])[is_water][
			np.where(np.any(dists<=gap/10.0,axis=1))[0]]
		#---collect waters not found in the excludes list of residues that overlap with not-water
		#---note that this command fails on redundant residues
		surviving_water = np.all((np.all((
			np.tile(excludes,(len(residue_indices),1))!=np.tile(residue_indices,(len(excludes),1)).T),
			axis=1),is_water),axis=0)
		#---remove waters that lie outside the box
		insiders = np.all([np.all((points[:,ii]>=0,points[:,ii]<=i),axis=0) 
			for ii,i in enumerate(boxvecs)],axis=0)
		surviving_indices = np.any((is_not_water,surviving_water,insiders),axis=0)
		lines = incoming['lines']
		lines = lines[:2]+list(np.array(incoming['lines'][2:-1])[surviving_indices])+lines[-1:]
		xyzs = list(points[surviving_indices])
		write_gro(lines=lines,xyzs=xyzs,output_file=wordspace.step+'solvate.gro')
	else: filecopy(wordspace['step']+'solvate-dense.gro',wordspace['step']+'solvate.gro')

@narrate
def minimize(name,method='steep'):

	"""
	minimize(name,method='steep')
	Standard minimization procedure.
	"""

	gmx('grompp',base='em-%s-%s'%(name,method),top=name,structure=name,
		log='grompp-%s-%s'%(name,method),mdp='input-em-%s-in'%method,skip=True)
	assert os.path.isfile(wordspace['step']+'em-%s-%s.tpr'%(name,method))
	gmx('mdrun',base='em-%s-%s'%(name,method),log='mdrun-%s-%s'%(name,method))
	filecopy(wordspace['step']+'em-'+'%s-%s.gro'%(name,method),
		wordspace['step']+'%s-minimized.gro'%name)
	checkpoint()

@narrate
def write_top(topfile):

	"""
	write_top(topfile)
	Write the topology file.
	"""

	#---always include forcefield.itp
	if 'ff_includes' not in wordspace: wordspace['ff_includes'] = ['forcefield']		
	with open(wordspace['step']+topfile,'w') as fp:
		#---write include files for the force field
		for incl in wordspace['ff_includes']:
			fp.write('#include "%s.ff/%s.itp"\n'%(wordspace['force_field'],incl))
		#---write include files
		if 'itp' not in wordspace: wordspace['itp'] = []
		for itp in wordspace['itp']: fp.write('#include "'+itp+'"\n')
		#---write system name
		fp.write('[ system ]\n%s\n\n[ molecules ]\n'%wordspace['system_name'])
		for key,val in wordspace['composition']: fp.write('%s %d\n'%(key,val))

@narrate
def read_top(topfile):

	"""
	Read a topology file to get the composition of the system.
	Note that the topfile path must be relative to the top level in case it's in inputs.
	"""

	with open(topfile,'r') as f: lines = f.read()
	chains = {}
	startline = [ii for ii,i in enumerate(lines.split('\n')) 
		if re.match('^(\s+)?\[(\s+)?molecules(\s+)?\]',i)][0]
	count_regex = '^(\w+)\s+([0-9]+)'
	components = [re.findall(count_regex,line).pop()
		for line in lines.split('\n')[startline:] if re.match(count_regex,line)]		
	for name,count in components: component(name,count=int(count))

def include(name,ff=False):

	"""
	include(name)
	Add an ITP file to the itp (non-ff includes) list but avoid redundancies 
	which cause errors in GROMACS.
	"""

	which = 'ff_includes' if ff else 'itp'
	if 'itp' not in wordspace: wordspace[which] = []
	if name not in wordspace[which]: wordspace[which].append(name)

def equilibrate_check(name):

	"""
	Check if the gro file for this step has been written.
	"""

	found = False
	fn = wordspace['step']+'md-%s.gro'%name
	if os.path.isfile(fn): 
		report('found %s'%fn,tag='RETURN')
		found = True
	return found

@narrate
def equilibrate(groups=None):

	"""
	equilibrate()
	Standard equilibration procedure.
	"""

	#---sequential equilibration stages
	seq = wordspace['equilibration'].split(',')
	for eqnum,name in enumerate(seq):
		if not equilibrate_check(name):
			gmx('grompp',base='md-%s'%name,top='system',
				structure='system' if eqnum == 0 else 'md-%s'%seq[eqnum-1],
				log='grompp-%s'%name,mdp='input-md-%s-eq-in'%name,
				flag=('' if not groups else '-n %s'%groups)+' -maxwarn 10')
			gmx('mdrun',base='md-%s'%name,log='mdrun-%s'%name,skip=True)
			assert os.path.isfile(wordspace['step']+'md-%s.gro'%name)
			checkpoint()

	#---first part of the equilibration/production run
	name = 'md.part0001'
	if not equilibrate_check(name):
		gmx('grompp',base=name,top='system',
			structure='md-%s'%seq[-1],
			log='grompp-0001',mdp='input-md-in',
			flag='' if not groups else '-n %s'%groups)
		gmx('mdrun',base=name,log='mdrun-0001')
		#---we don't assert that the file exists here because the user might kill it and upload
		checkpoint()

@narrate
def counterions(structure,top,resname="SOL",includes=None,ff_includes=None,gro='counterions'):

	"""
	counterions(structure,top)
	Standard procedure for adding counterions.
	The resname must be understandable by "r RESNAME" in make_ndx and writes to the top file.
	"""

	#---clean up the composition in case this is a restart
	for key in ['cation','anion','sol']:
		try: wordspace['composition'].pop(zip(*wordspace['composition'])[0].index(wordspace[key]))
		except: pass
	component(resname,count=wordspace['water_without_ions'])
	#---write the topology file as of the solvate step instead of copying them (genion overwrites top)
	write_top('counterions.top')
	gmx('grompp',base='genion',structure=structure,
		top='counterions',mdp='input-em-steep-in',
		log='grompp-genion')
	gmx('make_ndx',structure=structure,ndx='solvate-waters',
		inpipe='keep 0\nr %s\nkeep 1\nq\n'%resname,
		log='make-ndx-counterions-check')
	gmx('genion',base='genion',gro=gro,ndx='solvate-waters',
		cation=wordspace['cation'],anion=wordspace['anion'],
		flag='-conc %f -neutral'%wordspace['ionic_strength'],
		log='genion')
	with open(wordspace['step']+'log-genion','r') as fp: lines = fp.readlines()
	declare_ions = filter(lambda x:re.search('Will try',x)!=None,lines).pop()
	ion_counts = re.findall(
		'^Will try to add ([0-9]+)\+?\-? ([\w\+\-]+) ions and ([0-9]+) ([\w\+\-]+) ions',
		declare_ions).pop()
	for ii in range(2): component(ion_counts[2*ii+1],count=ion_counts[2*ii])
	component(resname,count=component(resname)-component(ion_counts[1])-component(ion_counts[3]))
	if includes:
		if type(includes)==str: includes = [includes]
		for i in includes: include(i)
	if ff_includes:
		if type(ff_includes)==str: ff_includes = [ff_includes]
		for i in ff_includes: include(i,ff=True)
	write_top('counterions.top')

def get_last_frame(tpr=False,cpt=False,top=False,ndx=False,itp=False):

	"""
	Get the last frame of any step in this simulation.
	This function is not narrated because the watch file is typically not ready until the new step 
	directory is created at which point you cannot use detect_last to get the last frame easily.
	"""

	if 'last_step' not in wordspace or 'last_part' not in wordspace:
		raise Exception('use detect_last to add last_step,last_part to the wordspace')
	last_step,part_num = wordspace['last_step'],wordspace['last_part']
	last_frame_exists = last_step+'md.part%04d.gro'%part_num
	if os.path.isfile(last_frame_exists): 
		shutil.copyfile(last_frame_exists,wordspace['step']+'system-input.gro')
	else:
		xtc = os.path.join(os.getcwd(),last_step+'md.part%04d.xtc'%wordspace['last_part'])
		if not os.path.isfile(xtc): raise Exception('cannot locate %s'%xtc)
		logfile = 'gmxcheck-%s-part%04d'%(last_step.rstrip('/'),part_num)
		gmx_run(' '.join([gmxpaths['gmxcheck'],'-f '+xtc]),log=logfile)
		with open(wordspace['step']+'log-'+logfile) as fp: lines = re.sub('\r','\n',fp.read()).split('\n')
		last_step_regex = '^Step\s+([0-9]+)\s*([0-9]+)'
		first_step_regex = '^Reading frame\s+0\s+time\s+(.+)'
		first_frame_time = [float(re.findall(first_step_regex,l)[0][0]) 
			for l in lines if re.match(first_step_regex,l)][0]
		last_step_regex = '^Step\s+([0-9]+)\s*([0-9]+)'
		nframes,timestep = [int(j) for j in [re.findall(last_step_regex,l)[0] 
			for l in lines if re.match(last_step_regex,l)][0]]
		#---! last viable time may not be available so this needs better error-checking
		last_time = float(int((float(nframes)-1)*timestep))
		last_time = round(last_time/10)*10
		#---interesting that trjconv uses fewer digits than the gro so this is not a perfect match
		#---note that we select group zero which is always the entire system
		#---note that we assume a like-named TPR file is available
		gmx_run(gmxpaths['trjconv']+' -f %s -o %s -s %s.tpr -b %f -e %f'%(
			xtc,'system-input.gro',xtc.rstrip('.xtc'),last_time,last_time),
			log='trjconv-last-frame',inpipe='0\n')
	#---list of files we must retrieve
	upstream_files = {
		'tpr':{'from':last_step+'md.part%04d.tpr'%part_num,'to':'system-input.tpr','required':True},
		'cpt':{'from':last_step+'md.part%04d.cpt'%part_num,'to':'system-input.cpt','required':True},
		'top':{'from':last_step+'system.top','to':'system.top','required':True},
		'ndx':{'from':last_step+'system-groups.ndx','to':'system-groups.ndx','required':False},
		}
	if not tpr: upstream_files.pop('tpr')
	if not cpt: upstream_files.pop('cpt')
	if not top: upstream_files.pop('top')
	if not ndx: upstream_files.pop('ndx')
	if itp:
		#---the itp flag means we need to acquire the force field and itp files from the previous run
		#---note that we are skipping the ff_includes here because they should be in a sources folder
		#---note that it was necessary to manually add ff_includes for an older protein run 
		if wordspace['itp']:
			for fn in wordspace['itp']: 
				upstream_files[fn] = {'from':last_step+'/'+fn,'to':fn,'required':True}
		if wordspace['sources']:
			for fn in wordspace['sources']: 
				upstream_files[fn] = {'from':last_step+'/'+fn,'to':fn,'required':True}
	#---! hardcoded force field options here but consider making this more general
	#---! why is this hacked below? with "or 1" (removed for testing)
	if wordspace['force_field'] in ['charmm27']:
		#---remove items which are always available in the GROMACS share folder
		for key in ['ions','tip3p','forcefield']: 
			if key in upstream_files: upstream_files.pop(key)
	#---copy files
	for key,val in upstream_files.items():
		dest = wordspace['step']+val['to']
		if not os.path.isfile(val['from']) and not os.path.isdir(val['from']):
			if val['required']: raise Exception('cannot find %s'%val['to'])
		elif not os.path.isfile(dest) and not os.path.isdir(dest): 
			if os.path.isfile(val['from']): shutil.copyfile(val['from'],wordspace['step']+val['to'])
			else: shutil.copytree(val['from'],wordspace['step']+val['to'])

@narrate
def read_gro(gro,**kwargs):

	"""
	Read a GRO file and return its XYZ coordinates and atomnames. 
	!Note that this is highly redundant with a cgmd_bilayer.read_molecule so you might replace that one.
	!RE-ADD NUMPY AND CENTER FOR reionize/cgmd_bilayer
	"""

	step = kwargs.get('step',wordspace.step)
	center = kwargs.get('center',False)
	with open(step+gro,'r') as fp: lines = fp.readlines()
	if center:
		import numpy as np
		pts = np.array([[float(j) for j in i.strip('\n')[20:].split()] for i in lines[2:-1]])
		pts -= np.mean(pts,axis=0)
		atom_names = np.array([i.strip('\n')[10:15].strip(' ') for i in lines[2:-1]])
	else:
		pts = [[float(j) for j in i.strip('\n')[20:].split()] for i in lines[2:-1]]
		atom_names = [i.strip('\n')[10:15].strip(' ') for i in lines[2:-1]]
	residue_names = [i[5:10].strip() for i in lines[2:-1]]
	residue_indices = [int(i[0:5].strip()) for i in lines[2:-1]]
	outgoing = {'points':pts,'atom_names':atom_names,'lines':lines,
		'residue_names':residue_names,'residue_indices':residue_indices}
	return outgoing

def write_gro(**kwargs):

	"""
	Write a GRO file with new coordinates.
	"""

	dotplace = lambda n: re.compile(r'(\d)0+$').sub(r'\1',"%8.3f"%float(n)).ljust(8)	
	input_file = kwargs.get('input_file',None)
	output_file = kwargs.get('output_file',None)
	if input_file:
		with open(incoming,'r') as fp: lines = fp.readlines()
	else: lines = kwargs.get('lines')
	xyzs = kwargs.get('xyzs')
	lines[1] = re.sub('^\s*([0-9]+)','%d'%(len(lines)-3),lines[1])
	for lnum,line in enumerate(lines[2:-1]):
		lines[2+lnum] = line[:20] + ''.join([dotplace(x) for x in xyzs[lnum]])+'\n'
	with open(output_file,'w') as fp: 
		for line in lines: fp.write(line)
