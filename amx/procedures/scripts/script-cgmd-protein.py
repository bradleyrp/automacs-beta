#!/usr/bin/python

settings = """
procedure: cgmd,protein
"""

import amx
amx.init(settings)
amx.start(amx.wordspace['step'])
amx.build_cgmd_protein(amx.wordspace['structure_name'])
