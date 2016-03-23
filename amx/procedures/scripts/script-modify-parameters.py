#!/usr/bin/python
execfile('/etc/pythonstart')

settings = """
step:               nve
procedure:          modify_parameters
equilibration:      None
mdp_specs:          {'group':'cgmd','input-md-in.mdp':None}
"""

from amx import *
init(settings)
try:
	if not wordspace['under_development']:
		previous_wordspace = resume(add=True,read_only=True)
		for key in ['sources','files','ff_includes']: 
			if key in previous_wordspace: wordspace[key] = previous_wordspace[key]		
		wordspace['last_step'],wordspace['last_part'] = detect_last()
		start(wordspace['step'])
		get_last_frame(tpr=True,cpt=True,ndx=True,top=True,itp=True)
	write_continue_script(continue_extend=1000,
		script='script-modify-parameters.sh',last_part=wordspace['last_part'])
	write_continue_script()
	write_mdp()
	checkpoint()
except KeyboardInterrupt as e: exception_handler(e,wordspace,all=True)
except Exception as e: exception_handler(e,wordspace,all=True)
else: write_wordspace(wordspace)
