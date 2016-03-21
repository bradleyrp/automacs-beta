#!/usr/bin/python
execfile('/etc/pythonstart')

settings = """
step:               large
procedure:          multiply
equilibration:      npt-bilayer
proceed:            True
nx:                 5
ny:                 5
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
	equilibrate(groups='system-groups')
except KeyboardInterrupt as e: exception_handler(e,all=True)
except Exception as e: exception_handler(e,all=True)
