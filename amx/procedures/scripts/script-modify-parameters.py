#!/usr/bin/python
execfile('/etc/pythonstart')

settings = """
step:               more
procedure:          modify_parameters
equilibration:      None
mdp_specs:          {'group':'cgmd','input-md-in.mdp':None}
"""

#cd ~/worker/automacs-bleed;rm -rf s03-more script-s03-more.* wordspace.json script-modify-parameters.py ; make program modify-parameters ; ./script-modify-parameters.py ; cd s03-more/;./script-modify-parameters.sh

from amx import *
init(settings)
try:
	if not wordspace['under_development']:
		previous_wordspace = resume(add=True,read_only=True)
		for key in ['sources','files','ff_includes']: 
			if key in wordspace: wordspace[key] = previous_wordspace[key]		
		wordspace['last_step'],wordspace['last_part'] = detect_last()
		start(wordspace['step'])
		get_last_frame(tpr=True,cpt=True,ndx=True,top=True)
	write_continue_script(continue_extend=1000,
		script='script-modify-parameters.sh',last_part=wordspace['last_part'])
	write_mdp()
except KeyboardInterrupt as e: exception_handler(e,wordspace,all=True)
except Exception as e: exception_handler(e,wordspace,all=True)
else: write_wordspace(wordspace)
