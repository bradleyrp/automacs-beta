#!/usr/bin/python

import re,os,subprocess
from amx import wordspace
from amx.base.functions import filecopy
from amx.base.gmxwrap import gmx,gmx_run,checkpoint
from amx.base.gromacs import gmxpaths
from amx.base.journal import *
from amx.procedures.common import *

"""
Protein homology modeling modules which wraps MODELLER.
"""

# no gromacs but these are not optional
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
doalign2d = True
if doalign2d:
	env = environ()
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
a = automodel(env,
	alnfile=afile,
	knowns=template_struct+template_struct_chain,
	sequence=target_seq,
	assess_methods=(assess.DOPE, assess.GA341))
a.starting_model = 1
a.ending_model = n_models
a.make()
"""

dna_mapping = {
	'UUU':'F','UUC':'F','UUA':'L','UUG':'L','UCU':'S','UCC':'s','UCA':'S','UCG':'S','UAU':'Y','UAC':'Y',
	'UAA':'STOP','UAG':'STOP','UGU':'C','UGC':'C','UGA':'STOP','UGG':'W','CUU':'L','CUC':'L','CUA':'L',
	'CUG':'L','CCU':'P','CCC':'P','CCA':'P','CCG':'P','CAU':'H','CAC':'H','CAA':'Q','CAG':'Q','CGU':'R',
	'CGC':'R','CGA':'R','CGG':'R','AUU':'I','AUC':'I','AUA':'I','AUG':'M','ACU':'T','ACC':'T','ACA':'T',
	'ACG':'T','AAU':'N','AAC':'N','AAA':'K','AAG':'K','AGU':'S','AGC':'S','AGA':'R','AGG':'R','GUU':'V',
	'GUC':'V','GUA':'V','GUG':'V','GCU':'A','GCC':'A','GCA':'A','GCG':'A','GAU':'D','GAC':'D','GAA':'E',
	'GAG':'E','GGU':'G','GGC':'G','GGA':'G','GGG':'G',} 
	
aacodemap = {'CYS': 'C', 'ASP': 'D', 'SER': 'S', 'GLN': 'Q', 'LYS': 'K',
	'ILE': 'I', 'PRO': 'P', 'THR': 'T', 'PHE': 'F', 'ASN': 'N', 
	'GLY': 'G', 'HIS': 'H', 'LEU': 'L', 'ARG': 'R', 'TRP': 'W', 'TER':'*',
	'ALA': 'A', 'VAL':'V', 'GLU': 'E', 'TYR': 'Y', 'MET': 'M','XAA':'X'}

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
		sequence = ''.join([''.join([aacodemap[j] for j in i[1].split()]) 
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
	else: raise Exception('need either REMARK 300 or SEQRES in your pdb file')
	return {'starting_residue':startres,'sequence':sequence}

@narrate
def get_pdb(code,chain):

	"""
	Download a PDB from the database. Takes a 4-character PDB code and downloads to the current step.
	"""

	template = code
	import urllib2
	response = urllib2.urlopen('http://www.rcsb.org/pdb/files/'+template+'.pdb')
	pdbfile = response.read()
	with open(wordspace.step+template+'.pdb','w') as fp: fp.write(pdbfile)
	return extract_sequence_pdb(filename=wordspace.step+template+'.pdb',chain=chain)

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
	gmx('editconf',structure=best,gro=wordspace.target_name+'.pdb',
		flag='-resnr %d'%wordspace.starting_residue,log='editconf-renumber')
	with open(wordspace.step+'best_structure_path','w') as fp: fp.write(best+'\n')
	