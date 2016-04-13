#!/usr/bin/python

settings = """
step:               continue
system name:        system
procedure:          continue
"""

from amx import *
init(settings)
try:
	if not wordspace['under_development']:
		start(wordspace['step']) 
		tprs = glob.glob('inputs/*.tpr')
		cpts = glob.glob('inputs/*.cpt')
		assert len(tprs)==1 and len(cpts)==1
		tpr,cpt = tprs[0],cpts[0]
		wordspace['tpr_start'] = tpr
		wordspace['cpt_start'] = cpt
	filecopy(tpr,wordspace.step+'md.part0001.tpr')
	filecopy(cpt,wordspace.step+'md.part0001.cpt')
	checkpoint()
	write_continue_script()
except KeyboardInterrupt as e: exception_handler(e,wordspace,all=True)
except Exception as e: exception_handler(e,wordspace,all=True)

"""
AUTOMACS procedure: continue a simulation from CPT/TPR
development notes:
	this script runs a standard continuation as long as you have TPR and a CPT file
	the above script autodetects the cpt and tpr from inputs
rapid development:
	make clean sure && make program continue && ./script-continue.py
see metarun_speedtest.py for batch implementation of this procedure

VVVVVVVV

in metarun make several copies
load cluster data somehow
run make cluster in each one
upload everything carte blanche
test on gordon
"""
