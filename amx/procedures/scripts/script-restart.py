#!/usr/bin/python

settings = """
step:               restart
equilibration:      None
new mdp:            True
regenerate tpr:     True
use cpt:            False
mdp settings:       {}
maxwarn:            1
"""

from amx import *
init(settings)
try:
	if not wordspace['under_development']:
		previous_wordspace = resume(add=True,read_only=True)
		for key in ['sources','files','ff_includes']: 
			if key in previous_wordspace: wordspace[key] = previous_wordspace[key]		
		wordspace['last_step'],wordspace['last_part'] = detect_last()
		wordspace_last = resume(read_only=True)
		start(wordspace['step'])
		get_last_frame(tpr=not wordspace['regenerate_tpr'],
			cpt=wordspace['use_cpt'],ndx=True,top=True,itp=True)
	write_continue_script(continue_extend=1000,maxwarn=wordspace['maxwarn'] if wordspace['maxwarn'] else 0,
		script='script-restart.sh',last_part=wordspace['last_part'])
	if wordspace['new_mdp'] and not os.path.isfile(str(wordspace['new_mdp'])):
		write_mdp(extras=previous_wordspace['mdp_specs'])
	else:
		if os.path.isfile(str(wordspace['new_mdp'])): new_mdp = wordspace['new_mdp']
		else: new_mdp = max(glob.iglob(wordspace['last_step']+'/*.mdp'),key=os.path.getctime)
		shutil.copy(new_mdp,wordspace['step']+'/input-md-in.mdp')
	if 'itp' in wordspace_last:
		for fn in wordspace_last['itp']: shutil.copy(wordspace['last_step']+'/'+fn,wordspace['step'])
	write_continue_script()
	if wordspace['regenerate_tpr']:
		#---! hacked
		gmx_run(gmxpaths['grompp']+
			' -f input-md-in.mdp -p system.top -c system-input.gro -maxwarn 10 '+
			'-o system-input.tpr -n system-groups.ndx',
			log='grompp-regenerate')
	checkpoint()
except KeyboardInterrupt as e: exception_handler(e,wordspace,all=True)
except Exception as e: exception_handler(e,wordspace,all=True)
else: write_wordspace(wordspace)

"""
AUTOMACS procedure: 
	restart a simulation from non-binary input files
development notes:
	this script was modified from the script-modify-parameters.py
	which used a pre-made mdp file copied from inputs
	this feature was retained with the "new_mdp" setting which can point to an mdp in inputs to copy it
	otherwise it will get the (gromacs output) mdp file from the last step using ctime
	switching gromacs versions:
		this script also lets you switch gromacs versions and continue a run from scratch
		this is easiest if you have environment modules installed with different version of gromacs 
		change the gromacs version by using ./config.py or ~/.automacs.py
		you will probably need to remake the TPR and cpt binaries which depend on version
		tell the restart to ignore the checkpoint by setting "use cpt: False"
		also set "regenerate tpr: True" to make a new TPR in the right version
		this uses the semi-hacked gmx_run command above to make a new TPR
	making mdp files
		1. if "new mdp" is a file then we will use that
		2. if it's True we will remake the mdps via mdp_specs from the previous steps
			recall that write_mdp then uses amx/procedures/parameters.py
			but this would be overridden by inputs/parameters.py
		3. if it's False/None we will get the last MDP
future development:
	later it would be useful to add a feature that generates the MDP from the parameters.py
	add an amx/procedures/parameters_gmx4.py for backwards compability with gromacs 4
	fix the gmx_run hack above
"""
