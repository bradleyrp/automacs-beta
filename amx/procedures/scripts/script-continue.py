#!/usr/bin/python

settings = """
step:               continue
system name:        system
from inputs:        False
"""

from amx import *
init(settings)
try:
	if not wordspace['under_development']:
		if wordspace['from_inputs']:
			tprs = glob.glob('inputs/*.tpr')
			cpts = glob.glob('inputs/*.cpt')
			assert len(tprs)==1 and len(cpts)==1
			tpr,cpt = tprs[0],cpts[0]
		else:
			last_step,last_part = detect_last()
			tpr = max(glob.iglob(last_step+'*.tpr'),key=os.path.getctime)
			cpt = max(glob.iglob(last_step+'*.cpt'),key=os.path.getctime)
		wordspace['tpr_start'] = tpr
		wordspace['cpt_start'] = cpt
		start(wordspace['step'])
	filecopy(tpr,wordspace.step+'md.part0001.tpr')
	filecopy(cpt,wordspace.step+'md.part0001.cpt')
	checkpoint()
	write_continue_script()
except KeyboardInterrupt as e: exception_handler(e,wordspace,all=True)
except Exception as e: exception_handler(e,wordspace,all=True)

"""
AUTOMACS procedure: 
continue a simulation from CPT/TPR
development notes:
	this script runs a standard continuation as long as you have TPR and a CPT file
	the above script autodetects the cpt and tpr from inputs
	this script is used for the speedtest found in metarun_speedtest.py
"""
