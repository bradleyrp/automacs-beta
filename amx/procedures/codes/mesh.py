#!/usr/bin/python

from numpy import *
import scipy
import scipy.spatial
import scipy.interpolate

#---sklearn is causing problems on OSX
#import sklearn
#from sklearn import manifold

#---geometry functions
triarea = lambda a : linalg.norm(cross(a[1]-a[0],a[2]-a[0]))/2.
vecnorm = lambda vec: array(vec)/linalg.norm(vec)
facenorm = lambda a: cross(a[1]-a[0],a[2]-a[0])

def reclock(points,ords=[0,1,2]):

	"""
	Reorders R2 points in clockwise order.
	"""

	rels = points[ords]-mean(points[ords],axis=0)
	return argsort(arctan2(rels[:,0],rels[:,1]))[::-1]

def beyonder(points,vecs,dims=[0,1],growsize=0.2,new_only=False,growsize_nm=None,return_ids=False):

	"""
	Given points and box vectors, this function will expand a bilayer patch across periodic boundaries. It is 
	meant to create inputs for meshing algorithms which later store data under the correct topology. The dims
	argument names the wrapping dimensions, which is typically XY.
	"""
	
	over = array([(i,j,k) for i in [-1,0,1] for j in [-1,0,1] for k in [-1,0,1]])
	over = array([list(j) for j in list(set([tuple(i) for i in over[:,:len(dims)]])) 
		if j != tuple(zeros(len(dims)))])
	vec2 = array([(vecs[i] if i in dims else 0.) for i in range(3)])	
	over2 = array([[(o[i] if i in dims else 0.) for i in range(3)] for o in over])
	alls = concatenate([points]+[points+i*vec2 for i in over2])
	#---save indices for extra points
	inds = concatenate([arange(len(points)) for i in range(len(over2)+1)])
	#---bugfix applied 2015.07.20 to fix incorrect ghost index numbering
	if 0: inds = concatenate([arange(len(points))]+[ones(len(over))*j for j in arange(len(points))])
	#---override the proportional growsize by a literal size
	if growsize_nm != None: growsize = max([growsize_nm/vecs[i] for i in dims])
	valids = where(all([all((alls[:,d]>-1*vec2[d]*growsize,alls[:,d]<vec2[d]*(1.+growsize)),axis=0) 
		for d in dims],axis=0))[0]
	if not return_ids: return alls[valids]
	else: return alls[valids],inds[valids].astype(int)

def torusnorm(pts1,pts2,vecs):

	"""
	Compute distances between points on a torus.
	"""

	cd = array([scipy.spatial.distance.cdist(pts1[:,d:d+1],pts2[:,d:d+1]) for d in range(2)])
	cd[0] -= (cd[0]>vecs[0]/2.)*vecs[0]
	cd[1] -= (cd[1]>vecs[1]/2.)*vecs[1]
	cd2 = linalg.norm(cd,axis=0)
	return cd2

def makemesh(pts,vec,growsize=0.2,curvilinear_neighbors=10,
	curvilinear=True,debug=False,growsize_nm=None,excise=True,areas_only=False):

	"""
	Function which computes curvature and simplex areas on a standard mesh.
	"""

	nmol = len(pts)
	pts = pts
	vec = vec
	if debug: 
		import time
		st = time.time()
		print "[STATUS] start makemesh %0.2f"%(time.time()-st)
	ptsb,ptsb_inds = beyonder(pts,vec,growsize=growsize,growsize_nm=growsize_nm,return_ids=True)
	if debug: print "[STATUS] project curvilinear="+str(curvilinear)+" %0.2f"%(time.time()-st);st=time.time()
	#---if curvilinear then use the isomap otherwise project onto the xy plane
	if curvilinear: proj = manifold.Isomap(curvilinear_neighbors,2).fit_transform(ptsb)
	else: proj = ptsb[...,:2]
	if debug: print "[STATUS] delaunay %0.2f"%(time.time()-st);st=time.time()
	if debug: print "[STATUS] shape="+str(shape(ptsb))
	dl = scipy.spatial.Delaunay(proj)
	if debug: print "[STATUS] reclock %0.2f"%(time.time()-st);st=time.time()
	simplices = array([a[reclock(ptsb[a])] for a in dl.simplices])
	#---rework simplices and ptsb to exclude superfluous points
	if debug: print "[STATUS] trim %0.2f"%(time.time()-st);st=time.time()
	#---relevants is a unique list of simplices with exactly one member that is equal to a core vertex point
	relevants = unique(concatenate([simplices[where(sum(simplices==i,axis=1)==1)[0]] for i in range(nmol)]))
	points = ptsb[relevants]
	ghost_indices = ptsb_inds[relevants]
	ptsb = points
	if debug: print "[STATUS] simplices %0.2f"%(time.time()-st);st=time.time()
	simplices = array([[where(relevants==r)[0][0] for r in s] 
		for s in simplices if all([r in relevants for r in s])])
	#---end rework
	if debug: print "[STATUS] areas %0.2f"%(time.time()-st);st=time.time()
	areas = array([triarea(ptsb[a]) for a in simplices])
	if areas_only: return {'simplices':simplices,'areas':areas,'nmol':nmol,'vec':vec,'points':points}
	if debug: print "[STATUS] facenorms %0.2f"%(time.time()-st);st=time.time()
	facenorms = array([vecnorm(facenorm(ptsb[a])) for a in simplices])	
	if debug: print "[STATUS] vertex-to-simplex %0.2f"%(time.time()-st);st=time.time()
	v2s = [where(any(simplices==i,axis=1))[0] for i in range(nmol)]
	if debug: print "[STATUS] vertex normals %0.2f"%(time.time()-st);st=time.time()
	vertnorms = array([vecnorm(sum(facenorms[ind]*\
		transpose([areas[ind]/sum(areas[ind])]),axis=0)) for ind in v2s])
	principals = zeros((nmol,2))
	nl = []
	if debug: print "[STATUS] curvatures %0.2f"%(time.time()-st);st=time.time()
	for v in range(nmol):
		neighbors = unique(simplices[where(any(simplices==v,axis=1))[0]])
		neighbors = neighbors[neighbors!=v]
		nl.append(neighbors)
		edges = ptsb[neighbors]-ptsb[v]
		weights = [areas[sl]/2./sum(areas[v2s[v]]) for sl in v2s[v]]
		tijs = [vecnorm(dot(identity(3)-outer(vertnorms[v],
			vertnorms[v].T),ab)) for ab in edges]
		kijs = [dot(vertnorms[v].T,ab)/linalg.norm(ab)**2 for ab in edges]
		ct = sum([weights[ind]*kijs[ind]*outer(tijs[ind],tijs[ind]) 
			for ind,i in enumerate(v2s[v])],axis=0)
		wsign = 1-2*(linalg.norm(array([1,0,0])+\
			vertnorms[v])<linalg.norm(array([1,0,0])-vertnorms[v]))
		wvi = vecnorm(array([1,0,0])+wsign*vertnorms[v])
		hm = identity(3)-2*outer(wvi,wvi.T)
		hhm = dot(dot(hm.T,ct),hm)
		principals[v] = -1*hhm[1,1],-1*hhm[2,2]
	if debug: print "[STATUS] PBC neighborlist %0.2f"%(time.time()-st);st=time.time()
	#---neighborlist under PBCs
	checksubssort,nlsubs = where(torusnorm(points[nmol:],points[:nmol],vec)==0)
	#if not all(checksubssort==arange(len(points)-nmol)): raise Exception('torusnorm lookup fail')
	try: nlpbc = [[(i if i<nmol else nlsubs[i-nmol]) for i in n] for n in nl]
	except: nlpbc = []
	gauss = (3*principals[:,0]-principals[:,1])*(3*principals[:,1]-\
		principals[:,0])
	mean = 1./2*((3*principals[:,0]-principals[:,1])+\
		(3*principals[:,1]-principals[:,0]))
	if debug: print "[STATUS] complete %0.2f"%(time.time()-st);st=time.time()
	return {'nmol':nmol,'vec':vec,'simplices':simplices,'points':points,
		'areas':areas,'facenorms':facenorms,'vertnorms':vertnorms,'principals':principals,
		'ghost_ids':ghost_indices,'gauss':gauss,'mean':mean}
