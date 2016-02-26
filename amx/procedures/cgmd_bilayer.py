#!/usr/bin/python

import re,os,subprocess
from amx import wordspace
from amx.base.journal import status
from amx.base.functions import filecopy
from amx.base.gmxwrap import gmx,gmx_run,checkpoint
from amx.base.gromacs import gmxpaths
from amx.base.journal import *
from amx.procedures.common import *
import numpy as np
from codes.mesh import *

"""
Coarse-grained bilayer builder.
"""

#---common command interpretations
command_library = """
grompp -f MDP.mdp -c STRUCTURE.gro -p TOP.top -o BASE.tpr -po BASE.mdp
mdrun -s BASE.tpr -cpo BASE.cpt -o BASE.trr -x BASE.xtc -e BASE.edr -g BASE.log -c BASE.gro -v NONE
editconf -f STRUCTURE.gro -o GRO.gro
genconf -f STRUCTURE.gro -nbox NBOX -o GRO.gro
make_ndx -f STRUCTURE.gro -o NDX.ndx
genion -s BASE.tpr -o GRO.gro -n NDX.ndx -nname ANION -pname CATION
trjconv -f STRUCTURE.gro -n NDX.ndx -s TPR.tpr -o GRO.gro
"""

#---customized parameters
mdp_specs = {
	'group':'cgmd',
	'input-em-steep-in.mdp':['minimize'],
	'input-em-cg-in.mdp':['minimize',{'integrator':'cg'}],
	'input-md-vacuum-pack-eq-in.mdp':['vacuum-packing'],
	'input-md-npt-bilayer-eq-in.mdp':['npt-bilayer'],
	'input-md-in.mdp':None,
	}

#---FUNCTIONS
#-------------------------------------------------------------------------------------------------------------

#---ensure decimal alignment for GRO format
dotplace = lambda n: re.compile(r'(\d)0+$').sub(r'\1',"%8.3f"%float(n)).ljust(8)

def rotation_matrix(axis,theta):

	"""
	Return the rotation matrix associated with counterclockwise rotation about
	the given axis by theta radians using Euler-Rodrigues formula.
	"""

	axis = np.asarray(axis)
	theta = np.asarray(theta)
	if all(axis==0): return np.identity(3) 
	axis = axis/sqrt(dot(axis, axis))
	a = cos(theta/2)
	b, c, d = -axis*sin(theta/2)
	aa, bb, cc, dd = a*a, b*b, c*c, d*d
	bc, ad, ac, ab, bd, cd = b*c, a*d, a*c, a*b, b*d, c*d
	return np.array([[aa+bb-cc-dd,2*(bc+ad),2*(bd-ac)],[2*(bc-ad),aa+cc-bb-dd,2*(cd+ab)],
		[2*(bd+ac),2*(cd-ab),aa+dd-bb-cc]])
		
def read_molecule(gro):

	"""
	Read a molecule in GRO form and return its XYZ coordinates and atomnames.
	"""

	with open(wordspace['lipid_structures']+'/'+gro+'.gro','r') as fp: rawgro = fp.readlines()
	pts = np.array([[float(j) for j in i.strip('\n')[20:].split()] for i in rawgro[2:-1]])
	pts -= mean(pts,axis=0)
	atomnames = np.array([i.strip('\n')[10:15].strip(' ') for i in rawgro[2:-1]])
	return pts,atomnames
		
def makeshape():

	"""
	Generate the midplane points for various bilayer shapes.
	"""
	
	shape = wordspace['shape']
	lx,ly,lz = [wordspace['l%s'%i] for i in 'xyz']
	binsize = wordspace['binsize']
	height = wordspace['height']
	if 'width' in wordspace: width = wordspace['width']
	mono_offset = wordspace['monolayer_offset']
	
	#---standard settings
	lenscale = 1.
	vecs = np.array([lx,ly,lz])
	x0,y0 = 1.5*vecs[:2]

	#---generate sample points
	griddims = np.array([round(i) for i in vecs/binsize])
	m,n = [int(i) for i in griddims[:2]]
	getgrid = np.array([[[i,j] for j in np.linspace(0,3*vecs[1]/lenscale,3*n)] 
		for i in np.linspace(0,3*vecs[0]/lenscale,3*m)])
	xys = np.concatenate(getgrid)
	pts = np.concatenate(([xys[:,0]],[xys[:,1]],[np.zeros(len(xys))])).T

	if shape == 'saddle':

		def bump(x,y,x0,y0,height,width):
			"""
			General function for producing a 2D Gaussian "dimple" or "bump".
			"""
			zs = height*np.exp(-(x-x0)**2/2/width**2)*\
				np.exp(-(y-y0)**2/2/width**2)
			return zs

		offsets = vecs[:2]/2.-2.
		bumpspots = [(0,1,1),(0,-1,1),(1,0,-1),(-1,0,-1)]
		for spot in bumpspots:
			pts[:,2] += bump(xys[:,0],xys[:,1],
				x0+offsets[0]*spot[0],y0+offsets[1]*spot[1],
				height*spot[2],width)
		ptsmid = np.concatenate(np.reshape(pts,(3*m,3*n,3))[m:2*m,n:2*n])
		ptsmid[:,0]-=vecs[0]
		ptsmid[:,1]-=vecs[1]
	
		if 0: meshplot(ptsmid,show='surf')
	
	elif shape == 'buckle':

		def buckle(x,y,height):
			zs = height*np.sin(x*2*pi/lx)
			return zs
		
		pts[:,2] += buckle(xys[:,0],xys[:,1],height)

	elif shape == 'flat': pts += 0
	else: raise Exception('\n[ERROR] unclear bilayer topography: %s'%shape)
	
	ptsmid = np.concatenate(np.reshape(pts,(3*m,3*n,3))[m:2*m,n:2*n])
	ptsmid[:,0]-=vecs[0]
	ptsmid[:,1]-=vecs[1]
	#---mesh the points
	#---note that curvlinear is slow and unnecessary for a flat membrane
	monolayer_mesh = makemesh(ptsmid,vecs,debug=False,curvilinear=False)
	return ptsmid,monolayer_mesh,vecs

@narrate
def build_bilayer(name,random_rotation=True):

	"""
	build_bilayer(name)
	Create a new bilayer according to a particular topography.
	"""
	
	#---collect the bilayer topography and the lipid points
	ptsmid,monolayer_mesh,vecs = makeshape()
	lpts,atomnames = read_molecule(wordspace['lipid'])
	mono_offset = wordspace['monolayer_offset']
	resname = wordspace['lipid']
	#---! hack for an extra buffer
	for i in range(2): vecs[i] += 0.5
	
	#---move the lipids into position and write a compbined GRO file	
	with open(wordspace['step']+name+'.gro','w') as fp:
		fp.write('%s\n'%wordspace['system_name']+str(2*len(ptsmid)*len(lpts))+'\n')
		resnr = 1
		#---loop over monolayers
		for mn in range(2):
			zvec = np.array([0,0,1]) if mn==0 else np.array([0,0,-1])
			for pnum,p in enumerate(ptsmid):
				status('lipid',i=pnum,looplen=len(ptsmid))
				#---for no rotation use xys = p+lpts
				#---rotate the lipids by the surface normal and offset by the half-bilayer 
				#---...thickness to the center
				offset = [1,-1][mn]*mono_offset*monolayer_mesh['vertnorms'][pnum]
				if random_rotation:
					random_angle = np.random.uniform()*2*np.pi
					lpts_copy = dot(rotation_matrix(zvec,random_angle),lpts.T).T
				else: lpts_copy = array(lpts)
				xys = p+offset+[1,-1][mn]*dot(
					rotation_matrix(cross(zvec,monolayer_mesh['vertnorms'][pnum]),
					dot(zvec,monolayer_mesh['vertnorms'][pnum])),lpts_copy.T).T
				fp.write('\n'.join([''.join([
					str(resnr).rjust(5),
					resname.ljust(5),
					atomnames[i].rjust(5),
					(str((resnr-1)*len(lpts_copy)+i+1).rjust(5))[:5],
					''.join([dotplace(x) for x in xys[i]])])
					for i in range(len(lpts_copy))])+'\n')
				resnr += 1
		fp.write(' '.join([dotplace(x) for x in vecs])+'\n')

	#---save the slab dimensions for solvation
	boxdims_old,boxdims = get_box_vectors(name)
	wordspace['bilayer_dimensions_slab'] = boxdims
	#---! need multiple lipid types
	component(wordspace['lipid'],count=resnr-1)

@narrate
def gro_combinator(*args,**kwargs):
	
	"""
	gro_combinator(*args,**kwargs)
	Concatenate an arbitrary number of GRO files.
	"""
	
	cwd = kwargs.pop('cwd','./')
	out = kwargs.pop('gro','combined')
	box = kwargs.pop('box',False)
	name = kwargs.pop('name','SYSTEM')

	collection = []
	for arg in args: 
		with open(cwd+arg+'.gro' if not re.match('^.+\.gro',arg) else cwd+arg) as fp: 
			collection.append(fp.readlines())
	with open(cwd+out+'.gro','w') as fp:
		fp.write('%s\n%d\n'%(name,sum(len(i) for i in collection)-len(collection)*3))
		for c in collection: 
			for line in c[2:-1]: fp.write(line)
		#---use the box vectors from the first structure
		if not box: fp.write(collection[0][-1])		
		else: fp.write(' %.3f %.3f %.3f\n'%tuple(box))

def read_gro(gro,cwd='./'):

	"""
	Read a GRO file into a standard form.
	May be wet with read_molecule.
	"""

	groform = {'resid':(0,5),'resname':(5,10),'name':(10,15),'index':(15,20),'xyz':(20,None)}
	with open(cwd+'/'+gro) as fp: rawgro = fp.readlines()
	structure,points = [],zeros((len(rawgro)-3,3))
	for line in rawgro[2:-1]: structure.append({key:line[slice(*val)] for key,val in groform.items()})
	for ii,i in enumerate(structure): points[ii] = [float(j) for j in i.pop('xyz').split()]
	return structure,points

@narrate
def adhere_protein_cgmd_bilayer(bilayer,combo,protein_complex=None):

	"""
	adhere_protein_cgmd_bilayer(bilayer,combo,protein_complex=None)
	Attach proteins to a CGMD (?) bilayer.
	"""

	cwd = wordspace['step']
	name = wordspace['system_name']
	space_scale = wordspace['space_scale']
	ncols,nrows = [wordspace[i] for i in ['ncols','nrows']]
	total_proteins = wordspace['total_proteins']
	z_shift = float(wordspace['z_shift'])
	lattice_type = wordspace['lattice_type']
	if protein_complex: adhere_structure = protein_complex
	else: adhere_structure = wordspace['protein_ready']

	#---create the mesh of focal points
	grid = [(i%ncols,int(i/nrows)) for i in arange(nrows*ncols)]
	if lattice_type == 'square': 
		vert = horz = space_scale
		offset = 0
		while len(grid)>total_proteins: grid.remove(-1)
	elif lattice_type == 'triangle': 
		horz,vert = space_scale,space_scale*sqrt(2.0)/2
		offset = space_scale/2.
		#---if total proteins is lower than the grid we remove from the end of odd rows
		scan = 1
		while len(grid)>total_proteins:
			grid.remove((ncols-1,scan))
			scan += 2
	else: raise Exception('unclear lattice type: %s'%lattice_type)
	grid_space = array([(horz*i+j%2.0*offset,vert*j) for i,j in array(grid).astype(float)])
	focii = concatenate((grid_space.T,[zeros(total_proteins)])).T
	if 0: meshpoints(focii)

	#---read the protein and bilayer
	combined,combined_points = read_gro(bilayer,cwd=wordspace['step'])
	protein,protein_points = read_gro(adhere_structure,cwd=wordspace['step'])

	#---take box vectors from the bilayer
	with open(cwd+'/'+bilayer) as fp: rawgro = fp.readlines()
	boxvecs = rawgro[-1]

	#---center the lattice in the middle of the XY plane of the box
	center_shift = array([float(j)/2. for j in boxvecs.split()[:2]]+
		[z_shift])-concatenate((mean(grid_space,axis=0),[0]))

	#---for each point in the lattice move the protein and combine the structures
	for translate in grid_space:
		combined = protein + combined
		combined_points = concatenate((protein_points+concatenate((translate,[0]))+center_shift,
			combined_points))

	#---remove the nearest lipid to the PIP2
	#---! this is a hack to find the only PIP2 after it's been added to the combined list
	lipid_center = mean(combined_points[array([ii for ii,i in enumerate(combined) 
		if i['resname']=='PIP2 '])],axis=0)
	#---get absolute indices of the standard lipids
	indices = array([ii for ii,i in enumerate(combined) if i['resname']=='DOPC'.ljust(5)]) 
	#---group indices by resid
	resids = array([int(combined[i]['resid']) for i in indices])
	#---centroids of the standard lipids
	cogs = array([mean(combined_points[indices][where(resids==r)],axis=0) for r in unique(resids)])
	nearest = argmin(linalg.norm(cogs-lipid_center,axis=1))
	nearest_resid = unique(resids)[nearest]
	excise = array([ii for ii,i in enumerate(combined) if i['resid']=='%5s'%nearest_resid 
		and i['resname']=='DOPC'.ljust(5)])
	combined = [i for ii,i in enumerate(combined) if ii not in excise]
	combined_points = [i for ii,i in enumerate(combined_points) if ii not in excise]
	component(wordspace['lipid'],count=component(wordspace['lipid'])-1)

	#---renumber residues and atoms
	if 0:
		resnr = 1
		last_resnr = int(combined[0]['resid'])
		for index,line in enumerate(combined):
			this_resnr = int(line['resid'])
			if this_resnr != last_resnr: resnr += 1
			line['resid'] = '%5s'%resnr
			line['index'] = '%5s'%index

	#---write the combined file
	with open(cwd+combo,'w') as fp:
		fp.write('%s\n%d\n'%(name,len(combined)))
		for index,line in enumerate(combined):
			fp.write(''.join([('%5s'%line[key])[:5] for key in ['resid','resname','name','index']]+
				[dotplace(x) for x in combined_points[index]])+'\n')
		fp.write(boxvecs)

@narrate
def solvate_bilayer(structure='vacuum'):
	
	"""
	Solvate a CGMD bilayer (possibly with proteins) avoiding overlaps.
	"""

	#---check the size of the slab
	incoming_structure = str(structure)
	boxdims_old,boxdims = get_box_vectors(structure)

	#---! standardize these?
	basedim = 3.64428
	waterbox = 'inputs/martini-water'

	#---make an oversized water box
	newdims = boxdims_old[:2]+[wordspace['solvent_thickness']]
	gmx('genconf',structure='martini-water',gro='solvate-empty-uncentered-untrimmed',
		nbox=' '.join([str(int(i/basedim+1)) for i in newdims]),log='genconf')

	#---trimming waters
	with open(wordspace['step']+'solvate-empty-uncentered-untrimmed.gro','r') as fp:
		lines = fp.readlines()
	modlines = []
	for line in lines[2:-1]:
		coords = [float(i) for i in line[20:].split()][:3]
		if all([coords[i]<newdims[i] for i in range(3)]): modlines.append(line)
	with open(wordspace['step']+'solvate-empty-uncentered.gro','w') as fp:
		fp.write(lines[0])
		fp.write(str(len(modlines))+'\n')
		for l in modlines: fp.write(l)
		fp.write(lines[-1])

	#---update waters
	structure='solvate-empty-uncentered'
	component('W',count=count_molecules(structure,'W'))

	#---translate the water box
	gmx('editconf',structure=structure,gro='solvate-water-shifted',
		flag='-translate 0 0 %f'%(wordspace['bilayer_dimensions_slab'][2]/2.),log='editconf-solvate-shift')

	#---combine and trim with new box vectors
	#---! skipping minimization?
	structure = 'solvate-water-shifted'
	boxdims_old,boxdims = get_box_vectors(structure)
	boxvecs = wordspace['bilayer_dimensions_slab'][:2]+[wordspace['bilayer_dimensions_slab'][2]+boxdims[2]]
	gro_combinator('%s.gro'%incoming_structure,structure,box=boxvecs,
		cwd=wordspace['step'],gro='solvate-dense')
	structure = 'solvate-dense'
	trim_waters(structure=structure,gro='solvate',boxcut=False,
		gap=wordspace['protein_water_gap'],method='cgmd',boxvecs=boxvecs)
	structure = 'solvate'
	component('W',count=count_molecules(structure,'W'))
	wordspace['bilayer_dimensions_solvate'] = boxvecs

@narrate
def add_proteins():

	"""
	Protein addition procedure for CGMD bilayers.
	"""

	#---assume that cgmd-protein step named the itp as follows
	filecopy(wordspace['last']+"Protein.itp",wordspace['step'])
	filecopy(wordspace['last']+wordspace['protein_ready'],wordspace['step'])
	filecopy(wordspace['last']+wordspace['lipid_ready'],wordspace['step'])
	gro_combinator(wordspace['protein_ready'],wordspace['lipid_ready'],
		cwd=wordspace['step'],gro='protein-lipid')
	adhere_protein_cgmd_bilayer(bilayer='vacuum-bilayer.gro',
		protein_complex='protein-lipid.gro',combo='vacuum.gro')
	#---assume inclusion of a partner lipid here
	include('Protein.itp')
	include('PIP2.itp')
	component('PIP2',count=wordspace['total_proteins'],top=True)
	component('Protein',count=wordspace['total_proteins'],top=True)
	#---custom additions to the mdp_specs to allow for protein groups
	for key in ['groups','temperature']:
		wordspace['mdp_specs']['input-md-npt-bilayer-eq-in.mdp'].append({key:'protein'})
		if wordspace['mdp_specs']['input-md-in.mdp'] == None:
			wordspace['mdp_specs']['input-md-in.mdp'] = []
		wordspace['mdp_specs']['input-md-in.mdp'].append({key:'protein'})
	print "???"
	import pdb;pdb.set_trace()
	write_mdp()
	print "DDD"

@narrate
def counterion_renamer(structure):

	"""
	Fix the ion names for MARTINI.
	"""

	with open(wordspace['step']+structure+'.gro') as fp: lines = fp.readlines()
	for lineno,line in enumerate(lines):
		if re.match('.{5}(CL|NA)',line):
			lines[lineno] = re.sub(re.escape(line[5:15]),
				'ION  '+line[5:10].strip().rjust(5),lines[lineno])
	with open(wordspace['step']+structure+'.gro','w') as fp:
		for line in lines: fp.write(line)

@narrate
def bilayer_middle(structure,gro):

	"""
	Move the bilayer to the middle of the z-coordinate of the box.
	Note that the protein adhesion procedure works best on a slab that is centered on z=0.
	This means that the bilayer will be broken across z=0.
	For visualization it is better to center it.
	"""

	gmx('make_ndx',ndx='system-dry',structure='counterions-minimized',
		inpipe="keep 0\nr %s || r ION || r %s || r %s\n!1\ndel 1\nq\n"%(
		wordspace['sol'],wordspace['anion'],wordspace['cation']),
		log='make-ndx-center')
	#---bilayer slab is near z=0 so it is likely split so we shift by half of the box vector
	gmx('trjconv',structure='counterions-minimized',gro='counterions-shifted',ndx='system-dry',
		flag='-trans 0 0 %f -pbc mol'%(wordspace['bilayer_dimensions_solvate'][2]/2.),
		tpr='em-counterions-steep',log='trjconv-shift',inpipe="0\n")
	#---center everything
	gmx('trjconv',structure='counterions-shifted',gro='system',ndx='system-dry',
		tpr='em-counterions-steep',log='trjconv-middle',inpipe="1\n0\n",flag='-center -pbc mol')

@narrate
def bilayer_sorter(structure,ndx='system-groups'):

	"""
	Divide the system into groups.
	"""

	if 'protein_ready' in wordspace:
		gmx('make_ndx',structure=structure,ndx='%s-inspect'%structure,
			log='make-ndx-%s-inspect'%structure,inpipe="q\n")
		with open(wordspace['step']+'log-make-ndx-%s-inspect'%structure) as fp: lines = fp.readlines()
		#---find the protein group because it may not be obvious in CGMD
		make_ndx_sifter = '^\s*([0-9]+)\s*Protein'
		protein_group = int(re.findall(make_ndx_sifter,
			next(i for i in lines if re.match(make_ndx_sifter,i)))[0])
		group_selector = "\n".join([
			"keep %s"%protein_group,
			"name 0 PROTEIN",
			#---! hacked
			" || ".join(['r '+r for r in [wordspace['lipid']]+['PIP2']]),
			"name 1 LIPIDS",
			" || ".join(['r '+r for r in ['W','ION',wordspace['cation'],wordspace['anion']]]),
			"name 2 SOLVENT",
			"0 | 1 | 2","name 3 SYSTEM","q"])+"\n"
	else:
		group_selector = "\n".join([
			"keep 0",
			"name 0 SYSTEM",
			" || ".join(['r '+r for r in [wordspace['lipid']]]),
			"name 1 LIPIDS",
			" || ".join(['r '+r for r in ['W','ION',wordspace['cation'],wordspace['anion']]]),
			"name 2 SOLVENT","q"])+"\n"
	gmx('make_ndx',structure='system',ndx=ndx,log='make-ndx-groups',
		inpipe=group_selector)

@narrate
def remove_jump(structure,tpr,gro):

	"""
	Correct that thing where the bilayer crosses the PBCs and gets split.
	"""

	gmx('make_ndx',ndx=structure,structure=structure,inpipe="keep 0\nq\n",log='make-ndx-nojump')	
	gmx('trjconv',ndx=structure,structure=structure,gro=gro,tpr=tpr,
		log='trjconv-%s-nojump'%structure,flag='-pbc nojump')
	os.remove(wordspace['step']+'log-'+'make-ndx-nojump')

def vacuum_pack(structure='vacuum',name='vacuum-pack',gro='vacuum-packed'):

	"""
	Pack the lipids in the plane, gently.
	"""

	gmx('grompp',base='md-%s'%name,top='vacuum',
		structure=structure,log='grompp-%s'%name,mdp='input-md-%s-eq-in'%name,
		flag='-maxwarn 100')
	gmx('mdrun',base='md-%s'%name,log='mdrun-%s'%name,skip=True)
	remove_jump(structure='md-%s'%name,tpr='md-'+name,gro='md-%s-nojump'%name)
	filecopy(wordspace['step']+'md-%s-nojump.gro'%name,wordspace['step']+'%s.gro'%gro)
	boxdims_old,boxdims = get_box_vectors(gro)
	wordspace['bilayer_dimensions_slab'][:2] = boxdims_old[:2]
