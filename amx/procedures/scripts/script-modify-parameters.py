#!/usr/bin/python
execfile('/etc/pythonstart')

settings = """
step:               more
procedure:          modify_parameters
equilibration:      None
"""

from amx import *
init(settings)
try:
	if not wordspace['under_development']:
		wordspace['last_step'],wordspace['last_part'] = detect_last()
		start(wordspace['step'])
		get_last_frame(tpr=True,cpt=True)
	write_continue_script(script='script-modify-parameters.sh',start_part=wordspace['last_part']+1)
	write_mdp()
except KeyboardInterrupt as e: exception_handler(e,wordspace,all=True)
except Exception as e: exception_handler(e,wordspace,all=True)
else: write_wordspace(wordspace)
