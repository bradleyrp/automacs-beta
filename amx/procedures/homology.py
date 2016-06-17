#!/usr/bin/python

import re,os,subprocess,shutil
from amx import wordspace
from amx.base.functions import filecopy
from amx.base.gmxwrap import gmx,gmx_run,checkpoint
from amx.base.gromacs import gmxpaths
from amx.base.journal import *
from amx.procedures.common import *


"""
Protein homology modeling modules which wraps MODELLER.
"""

command_library = """
editconf -f STRUCTURE -o GRO
"""

mdp_specs = {}

# scripts
script_single = """
from modeller import *
from modeller.automodel import *
import sys

execfile('settings-homology.py')
class mymodel(automodel):
        def special_patches(self, aln):
                self.rename_segments(segment_ids=[template_struct_chain],
                                     renumber_residues=[starting_residue])
doalign2d = True
if doalign2d:
	env = environ()
        env.io.hetatm = True
        env.io.water = False
	aln = alignment(env)
	mdl = model(env,
		file=template_struct,
		model_segment=('FIRST:'+template_struct_chain, 'LAST:'+template_struct_chain))
	aln.append_model(mdl,
		align_codes=template_struct+template_struct_chain,
		atom_files=template_struct+'.pdb')
	aln.append(file=target_seq+'.ali', align_codes=target_seq)
	aln.align2d()
	aln.write(file='align2d.ali', alignment_format='PIR')
	aln.write(file='align2d.pap', alignment_format='PAP')
	afile = 'align2d.ali'
else:
	env = environ()
	aln = alignment(env)
	afile = 'align2d-custom.ali'
a = mymodel(env,
	alnfile=afile,
	knowns=template_struct+template_struct_chain,
	sequence=target_seq,
	assess_methods=(assess.DOPE, assess.GA341))
a.starting_model = 1
a.ending_model = n_models
a.make()
"""

script_vmd = """#!/usr/bin/python

\"\"\"
View the homology models in VMD. 
Note that this script must be run from *within* the step directory.
\"\"\"

import os,sys,glob
sys.path.insert(0,os.path.abspath('../'))
from amx.procedures.codes.vmdwrap import *
execfile('settings-homology.py')

v = VMDWrap(subdir=False)

# overload the loader
v.commons['load'] = \"\"\"
mol new GRO
mol delrep 0 top
\"\"\"

# align each to the first
v.commons['align'] = \"\"\"
set sel0 [atomselect top all]
set sel1 [atomselect 0 all]
set M [measure fit $sel0 $sel1]
$sel0 move $M
\"\"\"

v.do('standard')
for num,fn in enumerate(glob.glob('%s.*.pdb'%target_seq)):
	v.gro = fn
	v.do('load')
	if num>0: v.do('align')
	v.select(protein='protein',style='NewCartoon',structure_color=True)
v.show()

"""

dna_mapping = {
	'UUU':'F','UUC':'F','UUA':'L','UUG':'L','UCU':'S','UCC':'s','UCA':'S','UCG':'S','UAU':'Y','UAC':'Y',
	'UAA':'STOP','UAG':'STOP','UGU':'C','UGC':'C','UGA':'STOP','UGG':'W','CUU':'L','CUC':'L','CUA':'L',
	'CUG':'L','CCU':'P','CCC':'P','CCA':'P','CCG':'P','CAU':'H','CAC':'H','CAA':'Q','CAG':'Q','CGU':'R',
	'CGC':'R','CGA':'R','CGG':'R','AUU':'I','AUC':'I','AUA':'I','AUG':'M','ACU':'T','ACC':'T','ACA':'T',
	'ACG':'T','AAU':'N','AAC':'N','AAA':'K','AAG':'K','AGU':'S','AGC':'S','AGA':'R','AGG':'R','GUU':'V',
	'GUC':'V','GUA':'V','GUG':'V','GCU':'A','GCC':'A','GCA':'A','GCG':'A','GAU':'D','GAC':'D','GAA':'E',
	'GAG':'E','GGU':'G','GGC':'G','GGA':'G','GGG':'G',} 
	
aacodemap_3to1 = {'CYS': 'C', 'ASP': 'D', 'SER': 'S', 'GLN': 'Q', 'LYS': 'K',
	'ILE': 'I', 'PRO': 'P', 'THR': 'T', 'PHE': 'F', 'ASN': 'N', 
	'GLY': 'G', 'HIS': 'H', 'LEU': 'L', 'ARG': 'R', 'TRP': 'W', 'TER':'*',
	'ALA': 'A', 'VAL':'V', 'GLU': 'E', 'TYR': 'Y', 'MET': 'M','XAA':'X'}

aacodemap_1to3 = dict([(val,key) for key,val in aacodemap_3to1.items()])

@narrate
def export_modeller_settings(**kwargs):

	"""
	Write a settings file for the modeller script.
	"""
	
	filename = kwargs.pop('filename')
	#! better way to do this?
	with open(filename,'w') as fp:
		fp.write('#!/usr/bin/python\n\n')
		for var in kwargs.keys():
			if type(kwargs[var]) == str: val = '\''+str(kwargs[var])+'\''
			else: val = kwargs[var]
			fp.write(var+' = '+str(val)+'\n')

@narrate
def write_ali_file(fasta_linelen=50):

	"""
	Write an ALI file for MODELLER.
	"""

	with open(wordspace.step+wordspace.target_name+'.ali','w') as fp:
		fp.write('>P1;'+wordspace.target_name+'\n')
		fp.write('sequence:'+wordspace.target_name+':::::::0.00:0.00\n')
		seq = wordspace.target_sequence
		chopped = [seq[j*fasta_linelen:(j+1)*fasta_linelen] 
			for j in range(len(seq)/fasta_linelen+1)]
		chopped = [i for i in chopped if len(i) > 0]
		for i,seg in enumerate(chopped): fp.write(seg+('\n' if i < len(chopped)-1 else '*\n'))

def extract_sequence_backup(filename,chain):
  		  
        """
 	Extract the sequence of a PDB file using biopython
        
        Note that this may fail if there are missing residues - test
        """
 		
 	import Bio		
 	import Bio.PDB		
        import warnings
                

 	parser = Bio.PDB.PDBParser()		
        with warnings.catch_warnings():
                warnings.simplefilter(action="ignore")
                structure = parser.get_structure('this_pdb',filename)		
 	#---extract residue ID and name for non HETATM elements of all chains in the PDB		
 	seqs = {c.id:[(i.id[1],i.resname) 		
 		for i in c.get_residues() if i.id[0]==' '] 		
 		for c in structure.get_chains()}		

        sequence=''.join([aacodemap_3to1[i] for i in zip(*seqs[chain])[1]])	
        startres = int(seqs[chain][0][0])
	start_residue = startres

	if 'start_residue' in wordspace and wordspace['start_residue']: 
		start_residue = int(wordspace['start_residue'])
	stop_residue = len(sequence)+startres
	if 'stop_residue' in wordspace and wordspace['stop_residue']: 
		stop_residue = wordspace['stop_residue']
        if wordspace['sequence_info']:
                wordspace['sequence_info'][chain] = zip(range(start_residue,stop_residue),
                                                        sequence[start_residue-startres:stop_residue-startres])
        else: 
                wordspace['sequence_info'] = {chain:zip(range(start_residue,stop_residue),
                                                        sequence[start_residue-startres:stop_residue-startres])}

	return {
		'starting_residue':start_residue,
		'sequence':sequence[start_residue-startres:stop_residue-startres],
		'filename':os.path.basename(filename).split('.pdb')[0]}
 

@narrate
def extract_sequence_pdb(filename,chain):

	"""
	Extract the sequence and staring residue from a PDB file.
	This is a holdover from the original automacs.
	"""

	with open(filename) as fp: lines = fp.readlines()
	regex_seqres = '^SEQRES\s+[0-9]+\s+([A-Z])\s+[0-9]+\s+(.+)'
	regex_remark = '^REMARK\s300\s([A-Z]+)\s+'
	#---if SEQRES is present we get the sequence from it
	#---note that the seqres protocol below should handle missing residues even if they exist
	#---...at the beginning of the target sequence
	if any([re.match(regex_seqres,line) for line in lines]):
		seqresli = [li for li,l in enumerate(lines) if re.match(regex_seqres,l)]
		seqraw = [re.findall(regex_seqres,lines[li])[0] for li in seqresli]
		sequence = ''.join([''.join([aacodemap_3to1[j] for j in i[1].split()]) 
			for i in seqraw if i[0] == chain])
		missingli = [re.findall('^REMARK\s+([0-9]+)\sMISSING RESIDUES',l)[0] for li,l in enumerate(lines) 
			if re.match('^REMARK\s+([0-9]+)\sMISSING RESIDUES',l)]
		if missingli != []:
			if len(missingli)>1: raise Exception('cannot parse multiple MISSING RESIDUE notes')
			missingli = str(missingli[0])
			startres = int([
				re.findall('^REMARK\s+'+missingli+'\s+[A-Z]{3}\s+[A-Z]\s+([0-9]+)',l)[0] 
				for li,l in enumerate(lines)
				if re.match('^REMARK\s+'+missingli+'\s+[A-Z]{3}\s+[A-Z]\s+[0-9]+',l)][0])
		else: startres = int([line for line in lines if re.match('^ATOM',line)][0][22:25+1])
	elif any([re.match(regex_remark,line) for line in lines]):
		seqresli = [li for li,l in enumerate(lines) if re.match(regex_remark,l)]
		seqraw = [re.findall(regex_remark,lines[li])[0] for li in seqresli]
		sequence = ''.join(seqraw)
		startres = int([line for line in lines if re.match('^ATOM',line)][0][22:25+1])
	else: return False #file must contain either SEQRES or REMARK 300
	start_residue = startres
	if 'start_residue' in wordspace and wordspace['start_residue']: 
		start_residue = int(wordspace['start_residue'])
	stop_residue = len(sequence)+startres
	if 'stop_residue' in wordspace and wordspace['stop_residue']: 
		stop_residue = wordspace['stop_residue']
	wordspace['sequence_info'] = {chain:zip(range(start_residue,stop_residue),
		sequence[start_residue-startres:stop_residue-startres])}
	return {
		'starting_residue':start_residue,
		'sequence':sequence[start_residue-startres:stop_residue-startres],
		'filename':os.path.basename(filename).split('.pdb')[0]}

@narrate
def get_pdb():

	"""
	Download a PDB from the database or copy from file.
	"""

	#---if template is a path we copy the file
	if os.path.isfile(os.path.abspath(os.path.expanduser(wordspace.template))):
		template = os.path.basename(wordspace.template).split('.pdb')[0]
		shutil.copy(wordspace.template,wordspace.step)
	#---if template is a PDB code and a chain letter then we download it from the PDB
	elif re.match('^[A-Z0-9]{4}$',wordspace.template):
		import urllib2
		template,chain = wordspace.template,wordspace.template_chain
		response = urllib2.urlopen('http://www.rcsb.org/pdb/files/'+template+'.pdb')
		pdbfile = response.read()
		with open(wordspace.step+template+'.pdb','w') as fp: fp.write(pdbfile)
	else: 
		raise Exception(
			'\n[ERROR] unable to understand template "%s"'%wordspace.template+
			'\n[ERROR] supply a PDB,chain or a path')
        sequence=extract_sequence_pdb(filename=wordspace.step+template+'.pdb',chain=wordspace.template_chain)
        if not sequence:
                sequence=extract_sequence_backup(
                        filename=wordspace.step+template+'.pdb',chain=wordspace.template_chain)
        print sequence['starting_residue']
        return sequence

@narrate
def get_best_structure():

	"""
	Select the structure with the lowest DOPE.
	"""

	with open(wordspace.step+'script-single.log') as fp: lines = fp.readlines()
	regex_log = '^('+wordspace.target_name+'\.[A-Z0-9]+\.pdb)\s+(-?\d+\.?\d*)\s+(-?\d+\.?\d*)'
	results = [re.findall(regex_log,l)[0] for l in lines if re.match(regex_log,l)]
	results = [(i[0],float(i[1]),float(i[2])) for i in results]
	best = sorted(results,key=lambda x:x[1])[0][0]
	with open(wordspace.step+best) as fp: lines = fp.readlines()
	atom_record_start = [ll for ll,l in enumerate(lines) if l[:4]=='ATOM'][0]-1
	seqres = ""
        if wordspace['other_chains']:
                other_chain_atoms=replace_chains()
	for chain,details in wordspace['sequence_info'].items():
		seq = [aacodemap_1to3[i] for i in zip(*details)[1]]
		seqlen = len(seq)
		nrows = seqlen/13+(0 if seqlen%13==0 else 1)
		chunks = [seq[i*13:(i+1)*13] for i in range(nrows)]
		additions = ""
		for cnum,chunk in enumerate(chunks):
			additions += 'SEQRES  %-2d  %s %-4d  '%(cnum+1,chain,len(details))+' '.join(chunk)+'\n'
		seqres += additions
	lines.insert(atom_record_start,seqres)
        if wordspace['other_chains']: lines.append(other_chain_atoms)
	with open(wordspace.step+wordspace.target_name+'.pdb','w') as fp:
		for line in lines: fp.write(line)
	with open(wordspace.step+'best_structure_path','w') as fp: 
		fp.write(wordspace.target_name+'.pdb'+'\n')
	
@narrate
def replace_chains():
        
        """
        Add back any chains removed during modeling.
        May need to update to deal with more than one chain.
        """
        other_chain_atoms=[]
        with open(wordspace['template']) as fp: other_chain_lines = fp.readlines()
        for this_chain in wordspace['other_chains']:
                sequence=extract_sequence_pdb(filename=wordspace['template'],chain=this_chain)
                if not sequence:
                        sequence=extract_sequence_backup(filename=wordspace['template'],chain=this_chain)
                this_chain_atoms = [ll for ll,l in enumerate(other_chain_lines) if l[:4]=='ATOM' and l[21]==this_chain]
                other_chain_atoms.append([other_chain_lines[line] for line in this_chain_atoms])
        return ''.join([atom for chain in other_chain_atoms for atom in chain])


@narrate 
def write_view_script():

	"""
	Write a viewer script.
	"""

	with open(wordspace.step+'script-vmd.py','w') as fp: fp.write(script_vmd)
	os.chmod(wordspace.step+'script-vmd.py',0744)
	status('view script is ready at %sscript-vmd.py'%wordspace.step,tag='note')
