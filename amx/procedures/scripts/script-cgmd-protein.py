#!/usr/bin/python

settings = """
step:               protein
start structure:    inputs/STRUCTURE.pdb
requires:           cgmd_protein
martinize path:     inputs/martinize.py
"""

import amx
amx.init(settings)
amx.start(amx.wordspace['step'])
amx.filecopy(amx.wordspace['start_structure'],amx.wordspace['step']+'protein-start.pdb')
amx.build_cgmd_protein()
