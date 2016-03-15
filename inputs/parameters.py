#!/usr/bin/python -B

"""
MDP parameters lookups for AUTOMACS
this file should contain a nested dictionary called `mdpdefs`
this dictionary is effectively a tree which takes paths that assemble parameters
with a minimum amount of description commonly employed in the procedures codes
these codes will request new MDP files which are written according to settings below
more documentation is coming soon
"""

mdpdefs = {
	#---MDP settings group for atomistic CHARMM simulations
	'aamd':{
		#---defaults for redundant options (use None if only one)
		'defaults':{
			'potential':'verlet',
			'continue':'continue',
			'couple':None,
			'integrate':None,
			'constrain':None,
			'output':None,
			},
		#---standard options
		'potential':{
			'original':{
				},
			'verlet':{
				'cutoff-scheme':'verlet',
				'nstlist':20,
				'ns_type':'grid',
				'coulombtype':'PME',
				'pme_order':4,
				'fourierspacing':0.1125,
				'rcoulomb':0.9,
				'rlist':0.9,
				'rvdw':0.9,
				'pbc':'xyz',
				'dispcorr':'EnerPres',
				},
			},
		'couple':{
			'tcoupl':'V-rescale',
			'tc_grps':'Protein Non-Protein',
			'tau_t':'0.1 0.1',
			'ref_t':'300 300',
			'pcoupl':'Parrinello-Rahman',
			'pcoupltype':'isotropic',
			'tau_p':2.0,
			'ref_p':1.0,
			'compressibility':'4.5e-5',
			},
		'constrain':{
			'constraints':'h-bonds',
			'constraint_algorithm':'lincs',
			},
		'continue':{
			'continue':{'continuation':'yes'},
			'start':{'continuation':'no'},
			},
		'output':{
			'nstxout':20000,
			'nstvout':20000,
			'nstlog':1000,
			'nstenergy':1000,
			'nstxtcout':1000,		
			},
		'integrate':{
			'integrator':'md',
			'tinit':0,
			'dt':0.002,
			'nsteps':500000,
			'nstcomm':100,
			'nstcalcenergy':100,
			'comm-grps':'Protein non-Protein',
			},
		#---override for minimization
		'minimize':{
			'integrate':{
				'integrator':'steep',
				'nsteps':50000,
				'nstcomm':0,
				'emtol':10.0,
				'emstep':0.01,
				},
			'couple':{},
			'constrain':{'constraints':'none'},
			},
		#---override for NVT protein and solvent
		'nvt-protein':{
			'continue':'start',
			'output':{
				'nstxout':1000,
				'nstvout':1000,
				'nstlog':100,
				'nstenergy':100,
				'nstxtcout':500,		
				},		
			'couple':{
				'tcoupl':'V-rescale',
				'tau_t':'0.1 0.1',
				'tc_grps':'Protein Non-Protein',
				'ref_t':'300 300',
				'pcoupl':'no',
				},	
			'constrain':{
				'constraints':'all-bonds',
				'constraint_algorithm':'lincs',
				},
			'integrate':{
				'integrator':'md',
				'tinit':0,
				'dt':0.001,
				'nsteps':100000,
				'nstcomm':100,
				'nstcalcenergy':100,
				'comm-grps':'Protein non-Protein',
				},
			},
		#---override for NVT protein and solvent
		'nvt-protein-short':{
			'continue':'start',
			'output':{
				'nstxout':1000,
				'nstvout':1000,
				'nstlog':100,
				'nstenergy':100,
				'nstxtcout':500,		
				},		
			'couple':{
				'tcoupl':'V-rescale',
				'tc_grps':'Protein Non-Protein',
				'tau_t':'0.1 0.1',
				'ref_t':'300 300',
				'pcoupl':'no',
				},	
			'constrain':{
				'constraints':'h-bonds',
				'constraint_algorithm':'lincs',
				},
			'integrate':{
				'integrator':'md',
				'tinit':0,
				'dt':0.0001,
				'nsteps':100000,
				'nstcomm':100,
				'nstcalcenergy':100,
				'comm-grps':'Protein non-Protein',
				},
			},		
		#---override for NPT protein and solvent
		'npt-protein':{
			'continue':'start',
			'output':{
				'nstxout':1000,
				'nstvout':1000,
				'nstlog':100,
				'nstenergy':100,
				'nstxtcout':500,		
				},		
			'couple':{
				'tcoupl':'V-rescale',
				'tc_grps':'Protein Non-Protein',
				'tau_t':'0.1 0.1',
				'ref_t':'300 300',
				'pcoupl':'Berendsen',
				'pcoupltype':'isotropic',
				'tau_p':1.0,
				'ref_p':1.0,
				'compressibility':'4.5e-5',
				},	
			'constrain':{
				'constraints':'all-bonds',
				'constraint_algorithm':'lincs',
				},
			'integrate':{
				'integrator':'md',
				'tinit':0,
				'dt':0.001,
				'nsteps':10000,
				'nstcomm':100,
				'nstcalcenergy':100,
				'comm-grps':'Protein non-Protein',
				},
			},
		#---pull code
		'pull':{
			'pull':{
				'pull':'umbrella',
				'pull_ngroups':'2',
				'pull_ncoords':'1',
				'pull_group1_name':'pullbase',
				'pull_group2_name':'pulltip',
				'pull_coord1_type':'umbrella',
				'pull_coord1_groups':'1 2',
				'pull-dim':'N Y N',
				'pull_coord1_rate':'0.01',
				'pull_coord1_k':'1000',
				'pull_start':'yes',
				},
			},
		},
	#---MDP settings group for CGMD MARTINI simulations
	'cgmd':{
		#---defaults for redundant options (use None if only one)
		'defaults':{
			'potential':'verlet',
			'constrain':'none',
			'restrain':'none',
			'continue':'continue',
			'integrate':None,
			'output':None,
			'temperature':'none',
			'pressure':None,
			'groups':'none',
			'screening':'standard',
			},
		#---standard options
		'potential':{
			'original':{
				'cutoff-scheme':'group',
				'nstlist':10,
				'ns_type':'grid',
				'pbc':'xyz',
				'rlist':'1.2',
				'coulombtype':'Shift',
				'rcoulomb_switch':0.0,
				'rcoulomb':1.2,
				'vdw_type':'Shift',
				'rvdw_switch':0.9,
				'rvdw':1.2,
				'DispCorr':'No',
				},
			'verlet':{
				'cutoff-scheme':'verlet',
				'nstlist':20,
				'ns_type':'grid',
				'pbc':'xyz',
				'coulombtype':'cut-off',
				'coulomb-modifier':'Potential-shift-verlet',
				'rcoulomb':1.1,
				'vdw_type':'cut-off',
				'vdw-modifier':'Potential-shift-verlet',
				'rvdw':1.1,
				'DispCorr':'No',
				'verlet-buffer-tolerance':0.005,
				},
			},
		'screening':{
			'standard':{'epsilon_r':15},
			'off':{'epsilon_r':0},
			},
		'restrain':{
			'posre':{'define':'-DPOSRES'},
			'none':{},
			},			
		'constrain':{
			'none':{
				'constraints':'none',
				'constraint_algorithm':'Lincs',
				},
			},
		'continue':{
			'continue':{'continuation':'yes','gen_vel':'no','gen_seed':123123,},
			'start':{'continuation':'no','gen_vel':'yes','gen_seed':123123,},
			},
		'integrate':{
			'integrator':'md',
			'tinit':0.0,
			'dt':0.02,
			'nsteps':50000,
			'nstcomm':100,
			},
		'groups':{
			'none':{
				'comm-grps':'LIPIDS SOLVENT',
				'energygrps':'LIPIDS SOLVENT',
				},
			'protein':{
				'comm-grps':'LIPIDS SOLVENT PROTEIN',
				'energygrps':'LIPIDS SOLVENT PROTEIN',
				},
			'blank':{},
			},
		'output':{
		 	'nstxout':10000,
			'nstvout':10000,
			'nstfout':0,
			'nstlog':2000,
			'nstenergy':2000,
			'nstxtcout':2000,
			'xtc_precision':100,
			},
		'temperature':{
			'none':{
				'tcoupl':'v-rescale',
				'tc-grps':'LIPIDS SOLVENT',
				'tau_t':'1.0 1.0',
				'ref_t':'320 320',
				},
			'protein':{
				'tcoupl':'v-rescale',
				'tc-grps':'LIPIDS SOLVENT PROTEIN',
				'tau_t':'1.0 1.0 1.0',
				'ref_t':'320 320 320',
				},
			},
		'pressure':{
			'Pcoupl':'parrinello-rahman',
			'Pcoupltype':'semiisotropic',
			'tau_p':'12.0 12.0',
			'compressibility':'3e-4 3e-4',
			'ref_p':'1.0 1.0',
			},
		#---override for NPT bilayer and solvent
		'npt-bilayer':{
			'continue':'start',
			'integrate':{
				'integrator':'md',
				'tinit':0.0,
				'dt':0.01,
				'nsteps':100000,
				'nstcomm':100,
				},		
			'output':{
			 	'nstxout':10000,
				'nstvout':10000,
				'nstfout':0,
				'nstlog':100,
				'nstenergy':100,
				'nstxtcout':1000,
				'xtc_precision':100,
				},
			},
		#---override for minimization
		'minimize':{
			'groups':'blank',
			'temperature':{'tcoupl':'no'},
			'pressure':{'Pcoupl':'no'},
			'output':{
			 	'nstxout':500,
				'nstvout':500,
				'nstfout':0,
				'nstlog':500,
				'nstenergy':500,
				'nstxtcout':500,
				'xtc_precision':100,
				},
			'integrate':{
				'integrator':'steep',
				'tinit':0.0,
				'dt':0.01,
				'nsteps':100000,
				'nstcomm':1,
				'emtol':10,
				'emstep':0.01,
				},
			},		
		#---override for vacuum packing steps			
		'vacuum-packing':{
			'groups':'blank',
			'restrain':'posre',
			'screening':'off',
			'integrate':{
				'integrator':'md',
				'tinit':0.0,
				'dt':0.001,
				'nsteps':1000000,
				'nstcomm':10,
				},
			'temperature':{
				'tcoupl':'Berendsen',
				'tc-grps':'SYSTEM',
				'tau_t':1.0,
				'ref_t':310,
				'gen_temp':310,
				},
			'pressure':{
				'Pcoupl':'Berendsen',
				'Pcoupltype':'semiisotropic',
				'tau_p':'0.5 0.5',
				'compressibility':'3e-4 0',
				'ref_p':'1.0 1.0',
				},
			},
		},		
	}
