#!/usr/bin/python

import re,os,subprocess
from amx import wordspace
from amx.base.journal import status
from amx.base.functions import filecopy
from amx.base.gmxwrap import gmx,gmx_run,checkpoint
from amx.base.gromacs import gmxpaths
from amx.base.journal import *
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
"""

#---customized parameters
mdp_specs = {
	'group':'cgmd',
	'input-em-steep-in.mdp':['minimize'],
	'input-em-cg-in.mdp':['minimize',{'integrator':'cg'}],
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
def build_bilayer(name):

	"""
	build_bilayer(name)
	Create a new bilayer according to a particular topography.
	Requires the following settings:
		???
	"""
	
	#---collect the bilayer topography and the lipid points
	ptsmid,monolayer_mesh,vecs = makeshape()
	lpts,atomnames = read_molecule(wordspace['lipid'])
	mono_offset = wordspace['monolayer_offset']
	resname = 'DOPC'
	
	#---move the lipids into position and write a compbined GRO file	
	with open(wordspace['step']+name,'w') as fp:
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
				xys = p+offset+[1,-1][mn]*dot(
					rotation_matrix(cross(zvec,monolayer_mesh['vertnorms'][pnum]),
					dot(zvec,monolayer_mesh['vertnorms'][pnum])),lpts.T).T
				fp.write('\n'.join([''.join([
					str(resnr).rjust(5),
					resname.ljust(5),
					atomnames[i].rjust(5),
					(str((resnr-1)*len(lpts)+i+1).rjust(5))[:5],
					''.join([dotplace(x) for x in xys[i]])])
					for i in range(len(lpts))])+'\n')
				resnr += 1
		fp.write(' '.join([dotplace(x) for x in vecs])+'\n')

@narrate
def gro_combinator(*args,**kwargs):
	
	"""
	gro_combinator(*args,**kwargs)
	Concatenate an arbitrary number of GRO files.
	"""
	
	cwd = kwargs.pop('cwd','./')
	out = kwargs.pop('out','out.gro')
	name = kwargs.pop('name','SYSTEM')

	collection = []
	for arg in args: 
		with open(cwd+arg) as fp: collection.append(fp.readlines())
	with open(cwd+out,'w') as fp:
		fp.write('%s\n%d\n'%(name,sum(len(i) for i in collection)-len(collection)*3))
		for c in collection: 
			for line in c[2:-1]: fp.write(line)
		#---use the box vectors from the first structure
		fp.write(collection[0][-1])		

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
		combined += protein
		combined_points = concatenate((combined_points,
			protein_points+concatenate((translate,[0]))+center_shift))

	#---renumber residues and atoms
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
def write_top(topfile):

	"""
	write_top(topfile)
	Write the topology file.
	WET CODE DRIPPED FROM protein_atomstic.py
	"""

	#---always include forcefield.itp
	if 'includes' not in wordspace: wordspace['includes'] = ['forcefield']		
	with open(wordspace['step']+topfile,'w') as fp:
		#---write include files for the force field
		for incl in wordspace['ff_includes']:
			fp.write('#include "%s.ff/%s.itp"\n'%(wordspace['force_field'],incl))
		#---write include files
		for itp in wordspace['itp']: fp.write('#include "'+itp+'"\n')
		#---write system name
		fp.write('[ system ]\n%s\n\n[ molecules ]\n'%wordspace['system_name'])
		for key,val in wordspace['composition']: fp.write('%s %d\n'%(key,val))

@narrate
def minimize(name,method='steep'):

	"""
	minimize(name,method='steep')
	Standard minimization procedure.
	WET CODE DRIPPED FROM protein_atomstic.py
	"""

	gmx('grompp',base='em-%s-%s'%(name,method),top=name,structure=name,
		log='grompp-%s-%s'%(name,method),mdp='input-em-%s-in'%method,skip=True)
	gmx('mdrun',base='em-%s-%s'%(name,method),log='mdrun-%s-%s'%(name,method))
	filecopy(wordspace['step']+'em-'+'%s-%s.gro'%(name,method),
		wordspace['step']+'%s-minimized.gro'%name)
	checkpoint()