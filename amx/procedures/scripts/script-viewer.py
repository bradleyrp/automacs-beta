#!/usr/bin/python

settings = """
step: v03-look
video name: video
input gro: system.gro
viewbox: (800,800)
resolution: (2400,1800)
bonder: false
which view: yview
scale: scale by 2.5
max frames: 200
show trajectory: true
video size: None
use snapshot: false
view mode: ['video','live','snapshot'][0]
recipe_collection:|[
	'video aamd atomistic bilayer protein',
	'live aamd atomistic bilayer protein',
	][0]
"""

from amx import *
init(settings)
try:
	from amx.procedures.codes.vmdmake import vmdmake
	vmdmake.yamlparse = yamlparse
	vmdmake.bash = bash
	vmdmake.gmxpaths = gmxpaths
	#---stage 1: create trajectory with unbroken molecules
	if not wordspace['under_development']:
		wordspace['last_step'],wordspace['last_part'] = detect_last()
		start(wordspace.step)
		#---always get the last frame for viewing
		get_last_frame(tpr=True,cpt=False,ndx=True,top=False,itp=False)
		wordspace.trajectory_details = vmdmake.remove_box_jumps(step=wordspace.step,
			last_step=wordspace.last_step,last_part=wordspace.last_part)
		wordspace.under_development = 1
		write_wordspace(wordspace,outfile=wordspace.step+'wordspace.json')
	#---stage 2: prepare the viewer scripts
	view = vmdmake.VMDWrap(site=wordspace.step,gro='system-input.gro',
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
	#---stage 3: make snapshots if this is a video
	if wordspace.view_mode == 'video' and not wordspace['video_snaps']: 
		wordspace.video_snaps = view.video(dn='snapshots',snapshot=wordspace['use_snapshot'])
		wordspace.under_development = 2
		write_wordspace(wordspace,outfile=wordspace.step+'wordspace.json')
	elif wordspace.view_mode == 'video': 
		view.video_dn,view.snapshot = wordspace.video_snaps,wordspace['use_snapshot']
	#---stage 3: run show and create snapshots if making a video
	if wordspace.under_development < 3:
		text_mode = wordspace.view_mode in ['video','snapshot']
		view.show(quit=text_mode,text=text_mode)
		wordspace.under_development = 3
		write_wordspace(wordspace,outfile=wordspace.step+'wordspace.json')
	#---stage 4: render the video
	if wordspace.view_mode == 'video': 
		view.render(name=wordspace.video_name,size=wordspace.video_size)
	wordspace.under_development = 4
except KeyboardInterrupt as e: exception_handler(e,wordspace,all=True)
except Exception as e: exception_handler(e,wordspace,all=True)
