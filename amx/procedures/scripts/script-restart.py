#!/usr/bin/python

settings = """
step:               restart
procedure:          restart
equilibration:      None
maxwarn:            1
new mdp:            None
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
	write_continue_script(continue_extend=1000,maxwarn=wordspace['maxwarn'] if wordspace['maxwarn'] else 0,
		script='script-restart.sh',last_part=wordspace['last_part'])
	if wordspace['new_mdp']: new_mdp = wordspace['new_mdp']
	else: new_mdp = max(glob.iglob(wordspace['last_step']+'/*.mdp'),key=os.path.getctime)
	shutil.copy(new_mdp,wordspace['step']+'/input-md-in.mdp')
	wordspace_last = resume(step=1,read_only=True)
	for fn in wordspace_last['itp']: shutil.copy(wordspace['last_step']+'/'+fn,wordspace['step'])
	write_continue_script()
	checkpoint()
except KeyboardInterrupt as e: exception_handler(e,wordspace,all=True)
except Exception as e: exception_handler(e,wordspace,all=True)
else: write_wordspace(wordspace)

"""
NOTES
this script was modified from the script-modify-parameters.py
which used a pre-made mdp file
"""