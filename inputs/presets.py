#!/usr/bin/python

presets = {}

presets['saddle'] = """
system_name:        CGMD BILAYER
lipid_structures:   inputs/cgmd-lipid-structures
step:               bilayer
procedure:          cgmd,bilayer
shape:              saddle
lx:                 35
ly:                 35
lz:                 50
height:             8
width:              10
binsize:            0.9
monolayer_offset:   1.5
lipid:              DOPC.gro
"""

presets['buckle'] = """
system_name:        CGMD BILAYER
lipid_structures:   inputs/cgmd-lipid-structures
step:               bilayer
procedure:          cgmd,bilayer
shape:              buckle
lx:                 40
ly:                 20
lz:                 50
height:             6
binsize:            0.9
monolayer_offset:   1.5
lipid:              DOPC
"""

presets['flat'] = """
system_name:        CGMD BILAYER
lipid_structures:   inputs/cgmd-lipid-structures
step:               bilayer
procedure:          cgmd,bilayer
shape:              flat
lx:                 100
ly:                 100
lz:                 50
height:             6
binsize:            0.9
monolayer_offset:   1.5
lipid:              DOPC
"""