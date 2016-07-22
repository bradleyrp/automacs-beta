#!/usr/bin/python

"""
This module contains procedure-specific codes arranged in dedicated sub-modules.
All procedures have access to the general functions found in the :meth:`common <amx.procedures.common>` 
sub-module. Some simple procedures need only to use these common functions to complete their task, 
however most procedures require a set of custom functions. These custom functions should be written 
to dedicated sub-modules. The mapping between the procedure name (which is read from the settings block 
of the parent script) and the correct sub-module is defined in ``procedure_toc``. 

Any user who wishes to add a custom procedure to automacs should place its functions in a new, dedicated
sub-module here. To ensure that the parent script has access to the relevant functions, they must register
the sub-module in ``procedure_toc`` dictionary with a key that serves as the name of the procedure (and 
hence must be included as the ``procedure`` variable in settings block the parent script) and the value 
is the name of the python sub-module with the desired functions. Every time automacs is imported by the 
parent script, it also imports the corresponding procedures sub-module.
"""

procedure_toc = {
	'aamd,protein':'protein_atomistic',
	'cgmd,protein':'cgmd_protein',
	'cgmd,bilayer':'cgmd_bilayer',
	'cgmd,bilayer2':'cgmd_bilayer',
	'aamd,bilayer':'bilayer',
	'homology':'homology',
	'multiply':'multiply',
	'reionize':'reionize',
	}
