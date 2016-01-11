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

def build_bilayer(name):

	"""
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

