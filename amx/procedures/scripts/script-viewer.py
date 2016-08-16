#!/usr/bin/python

settings = """
step: look
step prefix: v
video name: video
input gro: system.gro
viewbox: (800,800)
resolution: (2400,1800)
bonder: false
which view: yview
scale: scale by 2.5
max frames: 10
show trajectory: true
view mode: ['video','live','snapshot'][0]
recipe_collection:|[
	'video aamd atomistic bilayer protein',
	'live aamd atomistic bilayer protein',
	][0]
"""

from amx import *
init(settings)
try:
	from amx.procedures.codes import vmdwrap
	vmdwrap.yamlparse = yamlparse
	vmdwrap.bash = bash
	vmdwrap.gmxpaths = gmxpaths
	if not wordspace['under_development']:
		wordspace['last_step'],wordspace['last_part'] = detect_last()
		start(wordspace['step'],prefix='v')
		#---always get the last frame for viewing
		get_last_frame(tpr=True,cpt=False,ndx=True,top=False,itp=False)
		wordspace.trajectory_details = vmdwrap.remove_box_jumps(step=wordspace.step,
			last_step=wordspace.last_step,last_part=wordspace.last_part)
	view = vmdwrap.VMDWrap(site=wordspace.step,gro='system-input.gro',
		res=wordspace.resolution,viewbox=wordspace.viewbox)
	#---if dynamics we prepare a trajectory with whole molecules
	if wordspace.show_trajectory:
		#---send trajectory files names
		view.__dict__.update(**wordspace.trajectory_details)
		#---use MDAnalysis to get the right frame counts
		import MDAnalysis
		uni = MDAnalysis.Universe(wordspace.step+view.gro,wordspace.step+view.xtc)
		stepskip = max(int(float(len(uni.trajectory))/wordspace.max_frames+1),1)
		view.__dict__.update(step=stepskip,frames='')
	view.do('load_dynamic' if wordspace.show_trajectory else 'load','standard')
	if wordspace.bonder: view.do('bonder')
	view.do(wordspace.which_view)
	if wordspace['scale']: view.command(wordspace.scale)
	for recipe in view.recipes_collect[nospaces(wordspace.recipe_collection)]: 
		view.recipe(nospaces(recipe))
	if wordspace.view_mode == 'video': wordspace.video_snaps = view.video()
	text_mode = wordspace.view_mode in ['video','snapshot']
	if not wordspace['video_show_complete']:
		wordspace.video_show_complete = view.show(quit=text_mode,text=text_mode)
	if wordspace.view_mode == 'video': view.render(name=wordspace.video_name)
	#---! cannot resume and rerender video if it completes successfully
except KeyboardInterrupt as e: exception_handler(e,wordspace,all=True)
except Exception as e: exception_handler(e,wordspace,all=True)
