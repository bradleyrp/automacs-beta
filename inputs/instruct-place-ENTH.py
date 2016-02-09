#!/usr/bin/python -i
execfile('/etc/pythonstart')

import sys,os,re
import numpy as np
import MDAnalysis
import yaml

#---SETTINGS

instruct = """
system_name: ENTH domain
lipid_structure: inputs/cgmd-lipid-structures/PIP2.gro
protein_structure: s01-protein/protein.gro
method: simple
reference_axis: [0,0,1]
group_up: all
group_down:      
  - resid 1-22
  - resid 68-72
group_origin:
  - resid 1-22
  - resid 68-72
lipid_head: [2,3,4]
lipid_pocket:
  - resid 3
  - resid 69
comments:
  methods for aligning proteins
    simple
      give two selection groups
      the selection groups each have a COM
      the vector between the ordered groups is aligned with the Z-AXIS
      after alignment give a single group the COM which gets the PIP2 headgroup plus an offset
    banana
      the long axis is tangent to the plane
      the second principal component is parallel to the normal with a sign to specify direction
      after alignment PIP2 are added relative to COMs for the headgroup with an offset
"""

#---FUNCTIONS

def rotation_matrix(axis,theta):

	"""
	Return the rotation matrix associated with counterclockwise rotation about
	the given axis by theta radians using Euler-Rodrigues formula.
	"""

	axis = np.asarray(axis)
	theta = np.asarray(theta)
	if all(axis==0): return np.identity(3) 
	axis = axis/np.sqrt(np.dot(axis,axis))
	a = np.cos(theta/2)
	b, c, d = -axis*np.sin(theta/2)
	aa, bb, cc, dd = a*a, b*b, c*c, d*d
	bc, ad, ac, ab, bd, cd = b*c, a*d, a*c, a*b, b*d, c*d
	return np.array([[aa+bb-cc-dd,2*(bc+ad),2*(bd-ac)],[2*(bc-ad),aa+cc-bb-dd,2*(cd+ab)],
		[2*(bd+ac),2*(cd-ab),aa+dd-bb-cc]])

lenscale = 10.
vecnorm = lambda x: x/np.linalg.norm(x)
dotplace = lambda n: re.compile(r'(\d)0+$').sub(r'\1',"%8.3f"%float(n)).ljust(8)

def rewrite_gro(xyzs,incoming,outfile):

	"""
	Rewrite a GRO file with new coordinates.
	"""
	
	with open(incoming,'r') as fp: lines = fp.readlines()
	for lnum,line in enumerate(lines[2:-1]):
		lines[2+lnum] = line[:20] + ''.join([dotplace(x) for x in xyzs[lnum]])+'\n'
	with open(outfile,'w') as fp: 
		for line in lines: fp.write(line)

def select_group(uni,spec):

	"""
	Given a group definition we find the centroid.
	"""
	
	#---a single string returns the centroid of the selection
	if type(spec) == str: return np.mean(uni.select_atoms(spec).coordinates()/lenscale,axis=0)
	#---if the group selection is a list we take the centroid of centroids of each selection
	elif type(spec) == list:
		cogs = [np.mean(uni.select_atoms(s).coordinates()/lenscale,axis=0) for s in spec]
		return np.mean(cogs,axis=0)
	else: raise Exception('unclear group selection: %s'%str(spec))

#---MAIN

instruct = yaml.load(instruct)
if instruct['method'] not in ['simple']: raise Exception('unclear method')
elif instruct['method'] == 'simple':

	#---collect points
	incoming = instruct['protein_structure']
	workdir = os.path.dirname(incoming)
	uni = MDAnalysis.Universe(incoming)
	sel = uni.select_atoms('all')
	pts_all = sel.coordinates()/lenscale
	pts_up = select_group(uni,instruct['group_up'])
	pts_down = select_group(uni,instruct['group_down'])	
	#---translate the down group to the origin
	for pts in [pts_all,pts_up,pts_down]: pts -= pts_down
	#---identify the axis between the up and down groups
	axis = vecnorm(pts_up-pts_down)
	#---identify the orthogonal axis to the protein axis and the reference axis
	refaxis = np.array(instruct['reference_axis'])
	orthaxis = vecnorm(np.cross(refaxis,axis))
	#---compute angle between reference axis and protein axis and the resulting rotation 
	angle = np.arccos(np.dot(refaxis,axis))
	rotation = rotation_matrix(orthaxis,angle)
	#---apply the rotation
	xyzs = np.dot(pts_all,rotation)
	protein_out = workdir+'/protein-rotated.gro'
	rewrite_gro(xyzs,incoming,protein_out)

	#---reread the file to zero-center the desired group	
	if 'group_origin' in instruct:
		uni = MDAnalysis.Universe(workdir+'/protein-rotated.gro')
		sel = uni.select_atoms('all')
		pts_origin = select_group(uni,instruct['group_origin'])
		rewrite_gro(sel.coordinates()/lenscale-pts_origin,protein_out,protein_out)
		uni = MDAnalysis.Universe(workdir+'/protein-rotated.gro')
		sel = uni.select_atoms('all')
		pts_origin = select_group(uni,instruct['group_origin'])

	#---if lipid pocket then rotate the lipid to the reference axis and move the head to the pocket
	if 'lipid_pocket' in instruct:
		#---rotate the lipid to the reference axis
		uni_lipid = MDAnalysis.Universe(instruct['lipid_structure'])
		lpts = uni_lipid.select_atoms('all').coordinates()/lenscale
		lpts -= np.mean(lpts,axis=0)
		#---take the first principal component as the axis
		axis = vecnorm(lpts[0]-lpts[-1])
		eigs = np.linalg.eig(np.dot(lpts.T,lpts))
		principal_axis_index = np.argsort(eigs[0])[-1]
		axis = vecnorm(eigs[1][:,principal_axis_index])
		xyzs = np.dot(lpts,rotation_matrix(vecnorm(np.cross(refaxis,axis)),
			np.arccos(np.dot(refaxis,axis)))) 
		#---translate the head to the pocket
		head_atoms = np.array(eval(str(instruct['lipid_head'])))
		uni = MDAnalysis.Universe(workdir+'/protein-rotated.gro')
		pts_down = select_group(uni,instruct['lipid_pocket'])
		shift = np.mean(xyzs[head_atoms],axis=0)-pts_down
		rewrite_gro(xyzs-shift,instruct['lipid_structure'],workdir+'/lipid-rotated.gro')

	if 0:
		protein_out = workdir+'/protein-rotated.gro'
		uni = MDAnalysis.Universe(protein_out)
		sel = uni.select_atoms('all')
		pts_all = sel.coordinates()/lenscale
		rewrite_gro(pts_all+[0,0,3],protein_out,protein_out)
		lipid_out = workdir+'/lipid-rotated.gro'
		uni = MDAnalysis.Universe(lipid_out)
		sel = uni.select_atoms('all')
		pts_all = sel.coordinates()/lenscale
		rewrite_gro(pts_all+[0,0,3],lipid_out,lipid_out)
