#!/usr/bin/python

"""
BILAYER BUILDER codes

under development
"""

"""
AMX SUPPLIES: cgmd,bilayer
AMX SUPPLIES: mycustomprocedu

"""

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
import random

#---common command interpretations
command_library = """
pdb2gmx -f STRUCTURE -ff FF -water WATER -o GRO.gro -p system.top -i BASE-posre.itp -missing NONE -ignh NONE
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
	!REPLACE WITH common.read_gro
	"""

	with open(wordspace['lipid_structures']+'/'+gro+'.gro','r') as fp: rawgro = fp.readlines()
	pts = np.array([[float(j) for j in i.strip('\n')[20:].split()] for i in rawgro[2:-1]])
	pts -= mean(pts,axis=0)
	atomnames = np.array([i.strip('\n')[10:15].strip(' ') for i in rawgro[2:-1]])
	return pts,atomnames

def random_lipids(total,composition,binsize):

	"""
	Generate a random 2D grid of lipids in an arrangement according to the aspect ratio.
	Note that this is currently designed for flat bilayers so the binsize spacing is on the XY plane.
	"""

	aspect = wordspace['aspect']
	names,complist = zip(*composition.items())
	if sum(complist) != 1.0: complist = [float(i)/sum(complist) for i in complist]
	counts = [int(round(total*i)) for i in complist]
	arrange = concatenate([ones(j)*jj for jj,j in enumerate(counts)])
	random.shuffle(arrange)
	#---morph to fit the aspect ratio
	side_y = int(ceil(sqrt(total/aspect)))
	side_x = aspect*side_y
	pts = binsize*concatenate(array(meshgrid(arange(side_x),arange(side_y))).T)
	#---our grid will always be slightly too large so we trim it randomly
	selects = array(sorted(sorted(range(len(pts)),key=lambda *args:random.random())[:total]))
	vecs = array([side_x*binsize,side_y*binsize])
	return pts[selects],vecs
		
def makeshape():

	"""
	Generate the midplane points for various bilayer shapes.
	"""
	
	shape = wordspace['shape']
	lz = wordspace['solvent_thickness']
	binsize = wordspace['binsize']
	#---are the monolayers symmetric?
	monolayer_other = wordspace.get('monolayer_other',None)
	composition_other = wordspace.get('composition_other',None)
	if not monolayer_other and composition_other or not composition_other and monolayer_other:
		raise Exception('you must specify both "monolayer other" and "composition other"')
	monolayers = [[wordspace['monolayer_top'],wordspace['composition_top']]]
	if monolayer_other: monolayers += [[monolayer_other,composition_other]]
	else: monolayers += [monolayers[0]]
	#---compute spots on the 2D grid where we will place the lipids
	#---! note that we are still in 2D so the grid-spacing is only accurate for the flat bilayer
	spots,vecs = zip(*[random_lipids(total,composition,binsize) for total,composition in monolayers])
	#---for asymmetric bilayers we choose the larger set of box vectors
	vecs = transpose([max(i) for i in transpose(vecs)])
	pts = [np.concatenate(([s[:,0]],[s[:,1]],[np.zeros(len(s))])).T for s in spots]
	#---! non-flat points will be stretched in Z hence not evenly spaced in 3-space
	#---! needs 2 monolayers
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
	
	#---! needs 2 monolayers
	elif shape == 'buckle':

		def buckle(x,y,height):
			zs = height*np.sin(x*2*pi/lx)
			return zs
		
		pts[:,2] += buckle(xys[:,0],xys[:,1],height)

	elif shape == 'flat': pts = [p+0 for p in pts]
	else: raise Exception('\n[ERROR] unclear bilayer topography: %s'%shape)
	#---previously used PBCs and selected the middle tile here before makemesh and then shifted to origin
	monolayer_meshes = [makemesh(p,vecs,debug=False,curvilinear=False) for p in pts]
	return pts,monolayer_meshes,array([v for v in vecs]+[lz])

@narrate
def build_bilayer(name,random_rotation=True):

	"""
	build_bilayer(name,random_rotation=True)
	Create a new bilayer according to a particular topography.
	"""
	
	#---collect the bilayer topography and the lipid points
	ptsmid,monolayer_mesh,vecs = makeshape()

	#---infer composition of the other monolayer
	if type(wordspace['composition_top'])==str: monolayer0 = {wordspace['composition_top']:1.0}
	else: monolayer0 = wordspace['composition_top']
	if 'composition_bottom' not in wordspace or not wordspace['composition_bottom']: 
		monolayer1 = dict(monolayer0)
	else: monolayer1 = wordspace['composition_bottom']
	nlipids0 = wordspace['monolayer_top']
	if 'monolayer_bottom' not in wordspace or not wordspace['monolayer_bottom']: nlipids1 = nlipids0
	else: nlipids1 = wordspace['monolayer_bottom']
	lipid_resnames = wordspace['composition_top'].keys()
	if wordspace['composition_bottom']: lipid_resnames += wordspace['composition_bottom']
	#---save for bilayer_sorter
	wordspace['lipids'] = list(set(lipid_resnames))

	lipids,lipid_order = {},[]
	for key in list(set(monolayer0.keys()+monolayer1.keys())):
		lpts,atomnames = read_molecule(key)
		lipids[key] = {'lpts':lpts,'atomnames':atomnames}
		lipid_order.append(key)

	#---prepare random grids
	identities = [zeros([nlipids0,nlipids1][mn]) for mn in range(2)]
	for mn,composition in enumerate([monolayer0,monolayer1]):
		names,complist = zip(*composition.items())
		#---allow non-unity complist sums so you can use ratios or percentages
		if sum(complist) != 1.0: complist = [float(i)/sum(complist) for i in complist]
		nlipids = [nlipids0,nlipids1][mn]
		counts = array([int(round(i)) for i in array(complist)*nlipids])
		identities[mn] = concatenate([ones(counts[ii])*lipid_order.index(lname) 
			for ii,lname in enumerate(names)])[array(sorted(range(nlipids),
			key=lambda *args:random.random()))]

	mono_offset = wordspace['monolayer_offset']
	#---we wish to preserve the ordering of the lipids so we write them in order of identity
	placements = [[] for l in lipid_order]
	#---loop over lipid types
	for lipid_num,lipid in enumerate(lipid_order):
		lpts = lipids[lipid]['lpts']
		#---loop over monolayers
		for mn in range(2):
			zvec = np.array([0,0,1]) if mn==0 else np.array([0,0,-1])
			#---loop over positions of this lipid type
			indices = where(identities[mn]==lipid_num)[0]
			for ii,index in enumerate(indices):
				status('placing %s'%lipid,i=ii,looplen=len(indices))
				#---begin move routine
				point = ptsmid[mn][index]
				offset = [1,-1][mn]*mono_offset*monolayer_mesh[mn]['vertnorms'][index]
				if random_rotation:
					random_angle = np.random.uniform()*2*np.pi
					lpts_copy = dot(rotation_matrix(zvec,random_angle),lpts.T).T
				else: lpts_copy = array(lpts)
				xys = point+offset+[1,-1][mn]*dot(
					rotation_matrix(cross(zvec,monolayer_mesh[mn]['vertnorms'][index]),
					dot(zvec,monolayer_mesh[mn]['vertnorms'][index])),lpts_copy.T).T
				#---end move routine
				placements[lipid_num].append(xys)
	natoms = sum([sum(concatenate(identities)==ii)*len(lipids[i]['lpts']) 
		for ii,i in enumerate(lipid_order)])

	#---write the placed lipids to a file
	resnr = 1
	with open(wordspace['step']+name+'.gro','w') as fp:
		fp.write('%s\n'%wordspace['system_name']+'%d\n'%natoms)
		#---loop over lipid types
		for lipid_num,resname in enumerate(lipid_order):
			atomnames = lipids[resname]['atomnames']
			for xys in placements[lipid_num]:
				fp.write('\n'.join([''.join([
					str(resnr).rjust(5),
					resname.ljust(5),
					atomnames[i].rjust(5),
					(str((resnr-1)*len(xys)+i+1).rjust(5))[:5],
					''.join([dotplace(x) for x in xys[i]])])
					for i in range(len(xys))])+'\n')
				resnr += 1
		fp.write(' '.join([dotplace(x) for x in vecs])+'\n')

	#---save the slab dimensions for solvation
	boxdims_old,boxdims = get_box_vectors(name)
	wordspace['bilayer_dimensions_slab'] = boxdims
	#---save composition for topology
	for lipid_num,lipid in enumerate(lipid_order):
		component(lipid,count=len(placements[lipid_num]))

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
	if False: meshpoints(focii)

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
	#---! hack to specify which lipid to replace with PIP2
	replacement_lipid = 'DOPC'
	#---get absolute indices of the standard lipids
	indices = array([ii for ii,i in enumerate(combined) if i['resname']==replacement_lipid.ljust(5)]) 
	#---group indices by resid
	resids = array([int(combined[i]['resid']) for i in indices])
	#---centroids of the standard lipids
	cogs = array([mean(combined_points[indices][where(resids==r)],axis=0) for r in unique(resids)])
	nearest = argmin(linalg.norm(cogs-lipid_center,axis=1))
	nearest_resid = unique(resids)[nearest]
	excise = array([ii for ii,i in enumerate(combined) if i['resid']=='%5s'%nearest_resid 
		and i['resname']==replacement_lipid.ljust(5)])
	combined = [i for ii,i in enumerate(combined) if ii not in excise]
	combined_points = [i for ii,i in enumerate(combined_points) if ii not in excise]
	#---remove lipids in the composition
	component(replacement_lipid,count=component(replacement_lipid)-total_proteins)

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
	#---check the size of the water box
	waterbox = wordspace.water_box
	basedim,_ = get_box_vectors(waterbox)
	if not all([i==basedim[0] for i in basedim]):
		raise Exception('[ERROR] expecting water box "" to be cubic')
	else: basedim = basedim[0]
	#---make an oversized water box
	newdims = boxdims_old[:2]+[wordspace['solvent_thickness']]
	gmx('genconf',structure=waterbox,gro='solvate-empty-uncentered-untrimmed',
		nbox=' '.join([str(int(i/basedim+1)) for i in newdims]),log='genconf')
	#---trim the blank water box
	trim_waters(structure='solvate-empty-uncentered-untrimmed',
		gro='solvate-empty-uncentered',boxcut=True,boxvecs=newdims,
		gap=0.0,method=wordspace.atom_resolution)
	#---update waters
	structure='solvate-empty-uncentered'
	component(wordspace.sol,count=count_molecules(structure,wordspace.sol))
	#---translate the water box
	gmx('editconf',structure=structure,gro='solvate-water-shifted',
		flag='-translate 0 0 %f'%(wordspace['bilayer_dimensions_slab'][2]/2.),log='editconf-solvate-shift')
	#---combine and trim with new box vectors
	structure = 'solvate-water-shifted'
	boxdims_old,boxdims = get_box_vectors(structure)
	boxvecs = wordspace['bilayer_dimensions_slab'][:2]+[wordspace['bilayer_dimensions_slab'][2]+boxdims[2]]
	gro_combinator('%s.gro'%incoming_structure,structure,box=boxvecs,
		cwd=wordspace['step'],gro='solvate-dense')
	structure = 'solvate-dense'
	#---trim everything so that waters are positioned in the box without steric clashes
	trim_waters(structure=structure,gro='solvate',boxcut=False,
		gap=wordspace['protein_water_gap'],method=wordspace.atom_resolution,boxvecs=boxvecs)
	structure = 'solvate'
	nwaters = count_molecules(structure,wordspace.sol)/({'aamd':3.0,'cgmd':1.0}[wordspace.atom_resolution])
	if round(nwaters)!=nwaters: raise Exception('[ERROR] fractional water molecules')
	else: nwaters = int(nwaters)
	component(wordspace.sol,count=nwaters)
	wordspace['bilayer_dimensions_solvate'] = boxvecs
	wordspace['water_without_ions'] = nwaters

@narrate
def add_proteins():

	"""
	Protein addition procedure for CGMD bilayers.
	"""

	#---assume that cgmd-protein step named the itp as follows
	#---! assumes only a single protein ITP for now (needs further development)
	protein_itp_path, = glob.glob(wordspace['last']+'/Protein*.itp')
	protein_itp_fn = os.path.basename(protein_itp_path)
	filecopy(wordspace['last']+protein_itp_fn,wordspace['step'])
	filecopy(wordspace['last']+wordspace['protein_ready'],wordspace['step'])
	filecopy(wordspace['last']+wordspace['lipid_ready'],wordspace['step'])
	gro_combinator(wordspace['protein_ready'],wordspace['lipid_ready'],
		cwd=wordspace['step'],gro='protein-lipid')
	adhere_protein_cgmd_bilayer(bilayer='vacuum-bilayer.gro',
		protein_complex='protein-lipid.gro',combo='vacuum.gro')
	#---assume inclusion of a partner lipid here
	include(protein_itp_fn)
	include('PIP2.itp')
	component('PIP2',count=wordspace['total_proteins'],top=True)
	component(re.findall('^(.+)\.itp$',protein_itp_fn)[0],count=wordspace['total_proteins'],top=True)
	#---custom additions to the mdp_specs to allow for protein groups
	for key in ['groups','temperature']:
		wordspace['mdp_specs']['input-md-npt-bilayer-eq-in.mdp'].append({key:'protein'})
		if wordspace['mdp_specs']['input-md-in.mdp'] == None:
			wordspace['mdp_specs']['input-md-in.mdp'] = []
		wordspace['mdp_specs']['input-md-in.mdp'].append({key:'protein'})

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
def bilayer_sorter(structure,ndx='system-groups',protein=True):

	"""
	Divide the system into groups.
	"""

	if 'protein_ready' in wordspace or protein:
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
			" || ".join(['r '+r for r in wordspace['lipids']+['PIP2']]),
			"name 1 LIPIDS",
			" || ".join(['r '+r for r in [wordspace.sol,'ION',wordspace['cation'],wordspace['anion']]]),
			"name 2 SOLVENT",
			"0 | 1 | 2","name 3 SYSTEM","q"])+"\n"
	else:
		group_selector = "\n".join([
			"keep 0",
			"name 0 SYSTEM",
			" || ".join(['r '+r for r in wordspace['lipids']]),
			"name 1 LIPIDS",
			" || ".join(['r '+r for r in [wordspace.sol,'ION',wordspace['cation'],wordspace['anion']]]),
			"name 2 SOLVENT","q"])+"\n"
	gmx('make_ndx',structure='system',ndx=ndx,log='make-ndx-groups',
		inpipe=group_selector)

@narrate
def remove_jump(structure,tpr,gro,pbc='nojump'):

	"""
	Correct that thing where the bilayer crosses the PBCs and gets split.
	"""

	gmx('make_ndx',ndx=structure,structure=structure,inpipe="keep 0\nq\n",log='make-ndx-%s'%pbc)	
	gmx('trjconv',ndx=structure,structure=structure,gro=gro,tpr=tpr,
		log='trjconv-%s-%s'%(structure,pbc),flag='-pbc %s'%pbc)
	os.remove(wordspace['step']+'log-'+'make-ndx-%s'%pbc)

def vacuum_pack(structure='vacuum',name='vacuum-pack',gro='vacuum-packed',pbc='nojump'):

	"""
	Pack the lipids in the plane, gently.
	"""

	gmx('grompp',base='md-%s'%name,top='vacuum',
		structure=structure,log='grompp-%s'%name,mdp='input-md-%s-eq-in'%name,
		flag='-maxwarn 100')
	gmx('mdrun',base='md-%s'%name,log='mdrun-%s'%name,skip=True)
	if pbc:
		remove_jump(structure='md-%s'%name,tpr='md-'+name,gro='md-%s-%s'%(name,pbc))
		filecopy(wordspace['step']+'md-%s-%s.gro'%(name,pbc),wordspace['step']+'%s.gro'%gro)
	else: filecopy(wordspace['step']+'md-%s'%gro,wordspace['step']+'%s.gro'%gro)
	boxdims_old,boxdims = get_box_vectors(gro)
	wordspace['bilayer_dimensions_slab'][:2] = boxdims_old[:2]
