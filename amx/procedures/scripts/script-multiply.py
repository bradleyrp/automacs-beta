#!/usr/bin/python

settings = """
step:               large
procedure:          multiply
equilibration:      npt-bilayer
proceed:            True
minimize:           True
buffer:             [0.1,0.1,0.1]
nx:                 2
ny:                 2
"""

from amx import *
init(settings)
try:
	if not wordspace['under_development']:
		resume(add=True)
		wordspace['last_step'],wordspace['last_part'] = detect_last()
		start(wordspace['step'])
	get_last_frame()
	multiply(nx=wordspace['nx'],ny=wordspace['ny'])
	write_mdp()
	write_top('system.top')
	bilayer_sorter(structure='system',ndx='system-groups')
	structure = 'system'
	if 'minimize' in wordspace and wordspace.minimize: 
		structure = 'system-minimized'
		minimize('system')
	equilibrate(structure=structure,groups='system-groups')
except KeyboardInterrupt as e: exception_handler(e,wordspace,all=True)
except Exception as e: exception_handler(e,wordspace,all=True)
