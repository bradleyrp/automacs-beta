#!/usr/bin/python

presets = {}

presets['saddle'] = """
system_name:        CGMD BILAYER
lipid_structures:   inputs/cgmd-lipid-structures
step:               bilayer
procedure:          cgmd,bilayer
shape:              saddle
lx:                 35
ly:                 35
lz:                 50
height:             8
width:              10
binsize:            0.9
monolayer_offset:   1.5
lipid:              DOPC.gro
"""

presets['buckle'] = """
system_name:        CGMD BILAYER
lipid_structures:   inputs/cgmd-lipid-structures
step:               bilayer
procedure:          cgmd,bilayer
shape:              buckle
lx:                 40
ly:                 20
lz:                 50
height:             6
binsize:            0.9
monolayer_offset:   1.5
lipid:              DOPC
"""

presets['flat'] = """
system_name:        CGMD BILAYER
lipid_structures:   inputs/cgmd-lipid-structures
step:               bilayer
procedure:          cgmd,bilayer
shape:              flat
lx:                 40
ly:                 20
lz:                 50
height:             6
binsize:            0.9
monolayer_offset:   1.5
lipid:              DOPC
"""

settings = presets['flat']

import amx
amx.init(settings)
amx.start(amx.wordspace['step'])
#amx.write_mdp()
amx.build_bilayer(name='vacuum-bilayer.gro')

#---DEV
#-------------------------------------------------------------------------------------------------------------

if 0:

	xxxxsettings = """
	step:                protein
	procedure:           aamd,protein
	equilibration:       nvt,npt
	start structure:     inputs/STRUCTURE.pdb
	system name:         SYSTEM
	protein water gap:   3.0
	water:               tip3p
	force field:         charmm27
	water buffer:        1.2
	solvent:             spc216
	ionic strength:      0.150
	cation:              NA
	anion:               CL
	"""


	settings = """

	"""

	#---!
	import sys
	import numpy as np
	import re

	"""
	example saddle:
	./script-sculptor.py type=saddle lx=35 ly=35 lz=50 height=8 width=10 binsize=0.9 mono_offset=1.5 
		amxroot=/home/rpb/alternate/automacs/ lipid=DOPC dropspot=/home/rpb
	./script-sculptor.py type=buckle lx=40 ly=20 lz=50 height=6 binsize=0.9 mono_offset=1.5 
		amxroot=/home/rpb/alternate/automacs/ lipid=DOPC dropspot=/home/rpb

	"""

	argtypes = {
		'saddle':{
			'lx':float,
			'ly':float,
			'lz':float,
			'height':float,
			'width':float,
			'binsize':float,
			'mono_offset':float,
			'amxroot':str,
			'lipid':str,
			'dropspot':str,
			},
		'buckle':{
			'lx':float,
			'ly':float,
			'lz':float,
			'height':float,
			'binsize':float,
			'mono_offset':float,
			'amxroot':str,	
			'lipid':str,
			'dropspot':str,
			},
		}

	import amx
	from amx.mesh import *

	sys.argv += "type=saddle lx=35 ly=35 lz=50 height=8 width=10 binsize=0.9 mono_offset=1.5 ".split()
	sys.argv += "amxroot=/home/rpb/worker/automacs/ lipid=DOPC dropspot=/home/rpb".split()
	
	shape = [i.split('=')[1] for i in sys.argv[1:] if i.split('=')[0]=='type'][0]
	for key in [k for k in sys.argv[1:] if k.split('=')[0]!='type']:
		globals()[key.split('=')[0]] = argtypes[shape][key.split('=')[0]](key.split('=')[1])

	#---MAKE SHAPES
	#-------------------------------------------------------------------------------------------------------------

	if shape == 'saddle':

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

		def bump(x,y,x0,y0,height,width):
			"""
			General function for producing a 2D Gaussian "dimple" or "bump".
			"""
			zs = height*np.exp(-(x-x0)**2/2/width**2)*\
				np.exp(-(y-y0)**2/2/width**2)
			return zs

		#---construct a saddle
		offsets = vecs[:2]/2.-2.
		pts = np.concatenate(([xys[:,0]],[xys[:,1]],[np.zeros(len(xys))])).T
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

		def buckle(x,y,height):
			zs = height*np.sin(x*2*pi/lx)
			return zs
		
		#---construct a saddle
		pts = np.concatenate(([xys[:,0]],[xys[:,1]],[np.zeros(len(xys))])).T
		pts[:,2] += buckle(xys[:,0],xys[:,1],height)
		ptsmid = np.concatenate(np.reshape(pts,(3*m,3*n,3))[m:2*m,n:2*n])
		ptsmid[:,0]-=vecs[0]
		ptsmid[:,1]-=vecs[1]
	
		if 0: meshplot(ptsmid,show='surf')

	#---output directory
	cwd = os.path.expanduser('~') if 'dropspot' not in globals() else dropspot
			
	#---mesh the points
	mm = makemesh(ptsmid,vecs)

	def rotation_matrix(axis,theta):
		"""
		Return the rotation matrix associated with counterclockwise rotation about
		the given axis by theta radians using Euler-Rodrigues formula.
		"""
		axis = np.asarray(axis)
		theta = np.asarray(theta)
		axis = axis/sqrt(dot(axis, axis))
		a = cos(theta/2)
		b, c, d = -axis*sin(theta/2)
		aa, bb, cc, dd = a*a, b*b, c*c, d*d
		bc, ad, ac, ab, bd, cd = b*c, a*d, a*c, a*b, b*d, c*d
		return np.array([[aa+bb-cc-dd,2*(bc+ad),2*(bd-ac)],[2*(bc-ad),aa+cc-bb-dd,2*(cd+ab)],
			[2*(bd+ac),2*(cd-ab),aa+dd-bb-cc]])

	#---ensure decimal alignment for GRO format
	dotplace = lambda n: re.compile(r'(\d)0+$').sub(r'\1',"%8.3f"%float(n)).ljust(8)

	#---get lipid coordinates
	lipid_struct_file = amxroot+'/structs/'+lipid+'.gro'
	with open(lipid_struct_file,'r') as fp: rawgro = fp.readlines()
	lpts = np.array([[float(j) for j in i.strip('\n')[20:].split()] for i in rawgro[2:-1]])
	lpts -= mean(lpts,axis=0)
	resname = lipid
	atomnames = np.array([i.strip('\n')[10:15].strip(' ') for i in rawgro[2:-1]])

	#---write gro file
	resnr = 1
	print cwd
	raw_input('.')
	with open(cwd+'/prep-sculpt-uncentered.gro','w') as fp:
		fp.write('BILAYER SADDLE\n'+str(2*len(ptsmid)*len(lpts))+'\n')
		for mn in range(2):
			zvec = np.array([0,0,1]) if mn==0 else np.array([0,0,-1])
			for pnum,p in enumerate(ptsmid):
				amx.status('lipid',i=pnum,looplen=len(ptsmid))
				#---for no rotation use xys = p+lpts
				#---rotate the lipids by the surface normal and offset by the half-bilayer 
				#---...thickness to the center
				offset = [1,-1][mn]*mono_offset*mm['vertnorms'][pnum]
				xys = p+offset+[1,-1][mn]*dot(rotation_matrix(cross(zvec,mm['vertnorms'][pnum]),
					dot(zvec,mm['vertnorms'][pnum])),lpts.T).T
				fp.write('\n'.join([''.join([
					str(resnr).rjust(5),
					resname.ljust(5),
					atomnames[i].rjust(5),
					(str((resnr-1)*len(lpts)+i+1).rjust(5))[:5],
					''.join([dotplace(x) for x in xys[i]])])
					for i in range(len(lpts))])+'\n')
				resnr += 1
		fp.write(' '.join([dotplace(x) for x in vecs])+'\n')
	#call('editconf -f prep-sculpt-uncentered.gro -o prep-sculpt.gro -d -1.0',cwd=cwd)
	#amx.gmx('editconf',structure='vacuum-alone',gro='vacuum',
	#	log='editconf-vacuum-room',flag='-c -d %.2f'%amx.wordspace['water_buffer'])
	#print "[STATUS] wrote prep-sculpt.gro to "+cwd
	#with open(cwd+'/prep-sculpt-uncentered.gro','r') as fp: rawgro = fp.readlines()
	