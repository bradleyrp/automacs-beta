#!/usr/bin/python
execfile('/etc/pythonstart')

settings = """
step:               reionize
procedure:          reionize
equilibration:      npt
system name:        bilayer
sources:            ['charmm36.ff','lipids-tops']
files:              ['system.top','md.part0018.gro','input-md-in.mdp']
reionize specify:   {'some_divalents':{'Cal':{'quantity':10,'from':'NA','also_delete':10}}}
all ion names:      ['NA','Cal','MG','CL']
force field:        charmm36
itp:                ['lipids-tops/lipid.CHL1.itp','lipids-tops/lipid.DOPC.itp','lipids-tops/lipid.DOPE.itp','lipids-tops/lipid.DOPS.itp','lipids-tops/lipid.PI2P.itp','lipids-tops/lipid.POPC.itp']
ff includes:        ['forcefield','tips3p','ions']
"""

from amx import *
init(settings)
try:
	if not wordspace['under_development']: 
		start(wordspace.step)
	read_topology('system.top')
	#---assume the only gro in the files list is the incoming structure
	wordspace.structure, = [i for i in wordspace.files if re.match('^.+\.gro$',i)]
	wordspace.topology, = [i for i in wordspace.files if re.match('^.+\.top$',i)]
	estimate_concentrations(wordspace.structure)
	identify_candidate_replacements(
		structure=wordspace.structure,top=wordspace.topology,
		gro='system-input')
	name = 'md.part0001'
	groups = None
	gmx('grompp',base=name,top='system',
		structure='system-input',
		log='grompp-0001',mdp='input-md-in',
		flag='' if not groups else '-n %s'%groups)
	gmx('mdrun',base=name,log='mdrun-0001')
except KeyboardInterrupt as e: exception_handler(e,wordspace,all=True)
except Exception as e: exception_handler(e,wordspace,all=True)
else: write_wordspace(wordspace)

"""
development notes:
	there are many different ways to reionize a system
	this script was designed to reionize bilayers with sodium by adding a small quantity of calcium ions
	the "reionize_specify" key in the wordspace contains the simplest way to convent the procedure, and holds the following information:
		- a key,val pair for each substitution procedure, with only one for now
		- each procedure has a target ion (the key) and substitution rules in a subdictionary
		- we specify the quantity of new ions ("quantity")
		- we specify the name of the targets ("from")
		- and we allow for additional deletions ("also_delete") of the "from" ion to balance the charge
	restart command while developing:				
		make delstep 1 confident && cp inputs/script-reionize.py ./ && ./script-reionize.py
"""