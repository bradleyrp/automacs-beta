#!/usr/bin/python

settings = """
procedure:          videographer
step:               look
step prefix:        v
max frames:         200
style:              ['video','snapshot','live'][1]
"""

from amx import *
init(settings)

try:
	if not wordspace['under_development']:
		wordspace['last_step'],wordspace['last_part'] = detect_last()
		start(wordspace['step'],prefix='v')
		get_last_frame(tpr=True,cpt=False,ndx=True,top=False,itp=False)
		#---remove box jumps here
		xtc = wordspace['last_step']+'md.part%04d.xtc'%wordspace['last_part']
		bash(gmxpaths['trjconv']+
			' -f %s -s %s -o %s -pbc mol'%(
			os.path.join('../',xtc),
			'system-input.tpr',
			'md.part%04d.pbcmol.xtc'%wordspace['last_part']),
			log='trjconv-pbcmol',cwd=wordspace['step'],
			inpipe='0\n')
		bash(gmxpaths['trjconv']+
			' -f %s -s %s -o %s -pbc mol'%(
			'system-input.gro','system-input.tpr','system-input.pbcmol.gro'),
			log='trjconv-pbcmol-gro',cwd=wordspace['step'],inpipe='0\n')
	gro = wordspace['step']+'system-input.gro'
	tpr = wordspace['step']+'system-input.tpr'
	xtc = wordspace['last_step']+'md.part%04d.xtc'%wordspace['last_part']
	from amx.procedures.codes.vmdwrap import *
	if wordspace.style == 'video':
		#---select the right number of frames
		import MDAnalysis
		uni = MDAnalysis.Universe(gro,xtc)
		nframes = len(uni.trajectory)
		stepskip = max(int(float(nframes)/wordspace['max_frames']+1),1)
		#---render video
		v = VMDWrap(
			site=wordspace['step'],
			gro='system-input.gro',
			tpr='system-input.tpr',
			xtc='md.part%04d.pbcmol.xtc'%wordspace['last_part'],
			res=(1800,900),
			last=None,
			step=stepskip,
			backcolor='white',
			)
		v.do(*'load standard bonder xview'.split())
		v.command('scale by 2.5')
		v.select(lipids='not resname W and not resname ION and not water and not ions',smooth=True,
			style='Licorice 2.0 12.0 12.0',goodsell=True)
		v.video()
		v.show(text=True,quit=True,render='video',clean=True)
	elif wordspace.style == 'live':
		v = VMDWrap(
			site=wordspace['step'],
			gro='system-input.gro',
			tpr='system-input.tpr',
			res=(1800,900),
			backcolor='white',
			)
		v.do(*'load_structure standard bonder xview'.split())
		v.command('scale by 2.5')
		v.select(lipids='not resname W and not resname ION',smooth=True,style='lines')
		v.show()
	elif wordspace.style == 'snapshot':
		v = VMDWrap(
			site=wordspace['step'],
			gro='system-input.pbcmol.gro',
			tpr='system-input.tpr',
			res=(1800,900),
			backcolor='white',
			)
		v.do(*'load_structure standard bonder isoview'.split())
		v.command('scale by 2.5')
		v.select(lipids='not resname W and not resname ION',smooth=True,
			style='Licorice 2.0 12.0 12.0',goodsell=True)
		shot = ['set filename snapshot',
			'render Tachyon $filename "/usr/local/lib/vmd/tachyon_LINUXAMD64" '+\
			'-aasamples 12 %s -format TARGA -o %s.tga -res '+str(v.resx)+' '+str(v.resy),
			'exec convert $filename.tga $filename.png',
			'exec rm $filename.tga $filename']
		v.command('\n'.join(shot))
		v.show(text=True,quit=True)
	else: raise Exception('\n[ERROR] unclear videographer style "%s"'%wordspace.style)
except KeyboardInterrupt as e: exception_handler(e,wordspace,all=True)
except Exception as e: exception_handler(e,wordspace,all=True)

"""
AUTOMACS procedure: 
	make a video of the last part of a (cgmd lipid) simulation
development notes:
	currently only works on CGMD lipid simulations
	requires MDAnalysis and VMD
future development:
	add flags for slicing the trajectory, using multiple parts, etc
	add options for other systems
"""
