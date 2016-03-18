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
#---development
#import os,pickle
#execfile('amx/base/metatools.py')
#dev = os.path.isfile('wordspace.pkl')
init(settings,dev=dev,proceed=True)
try:
	if not dev:
		#---get previous wordspace
		resume(add=True)
		wordspace['last_step'],wordspace['last_part'] = detect_last()
		#---only start if not dev!
		start(wordspace['step'])
		get_last_frame()
		multiply(nx=wordspace['nx'],ny=wordspace['ny'])
		write_mdp()
		write_top('system.top')
		bilayer_sorter(structure='system',ndx='system-groups')
	equilibrate(groups='system-groups')
#---development
except KeyboardInterrupt: 
	pickle.dump(wordspace,open('wordspace.pkl','w'))
	report('interrupted!')
except Exception as e: 
	pickle.dump(wordspace,open('wordspace.pkl','w'))
	concise_error(e,all=True)
