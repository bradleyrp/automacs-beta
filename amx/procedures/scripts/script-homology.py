#!/usr/bin/python

settings = """
step:                homology
procedure:           homology
modeller path:       mod9.15
homology method:     point
template:            inputs/STRUCTURE.pdb
template chain:      A
other chains:        None
target name:         egfr_E710R
point mutation:      E710R
target sequence:     none
many models:         5
number HETATMs:      0
"""

from amx import *
init(settings)
start(wordspace.step)
#---template variable may be a PDB code or a path
pdb_attr = get_pdb()
wordspace.starting_residue = pdb_attr['starting_residue']
#---if point mutation figure out the right target sequence
if wordspace.homology_method == 'point':
	startres = wordspace.starting_residue
	target_sequence = list(pdb_attr['sequence']+'.'*wordspace.number_HETATMs)
	from_mutation,mutation_location,to_mutation = re.findall('([A-Z])([0-9]+)([A-Z])',
		wordspace.point_mutation)[0]
	mutation_location = int(mutation_location)
	if not target_sequence[mutation_location-startres]==from_mutation:
		raise Exception(
			'\n[ERROR] you have asked to change %s at residue %d '+
			'to %s but this residue is actually %s!'%(from_mutation,mutation_location,
			to_mutation,target_sequence[mutation_location-startres]))
	target_sequence[mutation_location-startres] = to_mutation
	wordspace.target_sequence = ''.join(target_sequence)
if not wordspace['other_chains']:
        export_modeller_settings(
                filename=wordspace.step+'settings-homology.py',
                template_struct=pdb_attr['filename'],
                template_struct_chain=wordspace.template_chain,
                target_seq=wordspace.target_name,
                n_models=wordspace.many_models,
                starting_residue=pdb_attr['starting_residue'])
if wordspace['other_chains']:
        other_chains_info={}
        for chain in wordspace['other_chains']:
                other_chains_info[chain]=wordspace['other_chains_info'][chain]['starting_residue']
        export_modeller_settings(
                filename=wordspace.step+'settings-homology.py',
                template_struct=pdb_attr['filename'],
                template_struct_chain=wordspace.template_chain,
                target_seq=wordspace.target_name,
                n_models=wordspace.many_models,
                starting_residue=pdb_attr['starting_residue'],
                other_chains=other_chains_info)
write_ali_file()
with open(wordspace.step+'script-single.py','w') as fp: fp.write(script_single)
bash(wordspace.modeller_path+' '+'script-single.py',cwd=wordspace.step)
get_best_structure()
write_view_script()
