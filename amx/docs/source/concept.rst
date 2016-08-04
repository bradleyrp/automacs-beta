
.. title :: Concept

Concept
=======

Automacs is a set of python codes which prepares molecular simulations using common tools, namely `GROMACS <http://www.gromacs.org/>`_ and `CHARMM <http://www.charmm.org/>`_. The purpose of this project is to ensure that simulations are prepared according to a standard method which also bundles simulation data with careful documentation. Automacs (hopefully) makes it possible to generate large simulation datasets with a minimum of description and so-called "manual" labor which invites mistakes and wastes time. Automacs codes are meant to be cloned once for each simulation rather than installed in a central location. This means that each simulation has a copy of the code used to create it.

"Overloaded Python"
~~~~~~~~~~~~~~~~~~~

High-level programming languages often rely on functions which can accept many different kinds of input while producing a consistent result. This is called `overloading <https://en.wikipedia.org/wiki/Function_overloading>`_. The automacs codes are overloaded in two ways. First, simulation data -- files, directories, etc -- for different procedures are organized in a uniform way. These file-naming conventions are described in the :doc:`framework <framework>`. Users who follow these rules can benefit from generic functions that apply to many different simulation types. For example, performing restarts or ensemble changes in GROMACS uses a single procedure, regardless of whether you are doing atomistic or coarse-grained simulations. Second, the procedure codes are organized to reflect the consistent naming conventions so that they can be used in as many situations as possible. The simulation-specific settings are separated from the generic, modular steps required to build a simulation so that users can simulate a variety of different systems without rewriting any code. In the next section, we will describe how this separation happens.

.. _concept_procedures:
Procedures
~~~~~~~~~~

Automacs executes simulations in two ways. Here we will describe the most basic procedures, which are built in to the codebase. In :ref:`chaining <chaining>` and :ref:`metarun <metarun>` we will describe how these procedures can be "chained" together or extended in order to create more complex simulations. 

A procedure consists of two pieces of code: a script and a library. Here we will walk through the atomistic protein simulation, which serves as a useful base-case procedure.

.. ! it would be useful to make the following emphasize-lines operate via regex

.. literalinclude :: ../../procedures/scripts/script-protein.py
  :tab-width: 4

The scripts are stored in ``amx/procedures/scripts`` and must all follow the same naming scheme: ``script-<name>.py``. These scripts also follow a standardized format. They must always start with a multiline string typically named ``settings``. This string must be immediately followed by the standardized import statements highlighted above, namely:

.. code-block :: python

  from amx import *
  init(settings)

Automacs has a very particular import scheme that ensures that both user-defined and built-in functions have access to a simulation-specific namespace which we call the ``wordspace``. [#wordspace]_ The wordspace is populated with the items defined in the settings block. The settings block consists of newline-separated ``key : value`` pairs where the value can be a block of Python code. If it fails to evaluate as Python code, it is interpreted either as a float, integer, or string.

.. literalinclude :: ../../procedures/scripts/script-protein.py
  :tab-width: 4
  :start-after: #!/usr/bin/python
  :end-before: from amx import *

Anything defined in the settings block will be populated in the ``wordspace`` dictionary. However some key names have a special meaning. For example, ``step`` will define and index a particular simulation step, and go on to house all of the output data for a discrete simulation step. In the example, automacs would store the protein simulation in ``s01-protein``. We prefer to use two-digit step numbering, but this is not a rule. This allows the user to easily pass information to a simulation procedure, using a single point of interface (the Factory uses this feature to automatically generate forms for these input parameters). Since the wordspace is shared across the codes, it can be used directly in the procedure script. In the example above, we use ``filecopy`` to move the starting structure into the step folder. Since all naming is handled by the ``wordspace``, all of the names and parameters are set in the ``settings`` block and everything that follows is general.

The wordspace is also accessible from small, modular simulation functions e.g. :meth:`minimize() <amx.procedures.common.minimize>`, which use the specific names written to the wordspace in order order to perform common simulation tasks on the particular simulation we are constructing. The :meth:`minimize() <amx.procedures.common.minimize>` function is applied several times in the atomistic protein procedure, once for the vacuum system, and again for the solvated system. 

These functions constitute the "library" portion of the procedure mentioned above. They are contained in a library so that the procedure scripts appear as a simple recipe using common ingredients (e.g. ``minimize`` and ``solvate``), and also so that these ingredients may be shared among different procedures. The source for the ``minimize`` function is reproduced below.

.. code-block :: python

    @narrate
    def minimize(name,method='steep'):

        """
        minimize(name,method='steep')
        Standard minimization procedure.
        """

        gmx('grompp',base='em-%s-%s'%(name,method),top=name,structure=name,
            log='grompp-%s-%s'%(name,method),mdp='input-em-%s-in'%method,skip=True)
        assert os.path.isfile(wordspace['step']+'em-%s-%s.tpr'%(name,method))
        gmx('mdrun',base='em-%s-%s'%(name,method),log='mdrun-%s-%s'%(name,method))
        filecopy(wordspace['step']+'em-'+'%s-%s.gro'%(name,method),
            wordspace['step']+'%s-minimized.gro'%name)
        checkpoint()

Most simulations require several minimization steps. The minimize function above is written for generic file names, but always performs the same task. It runs the GROMACS pre-processor followed by the ``mdrun`` executable. It copies the result to an obvious location, and also checks for errors after the preprocessor. If we start with e.g. ``solvate.gro``, calling ``minimize('solvate',method='steep')`` requires ``input-em-steep-in.md``, ``solvate.top``, and ``solvate.gro`` and will produce the following files:

.. code-block :: bash

  $ ls
  em-solvate-steep.tpr   em-solvate-steep.mdp         em-solvate-steep.gro 
  em-solvate-steep.log   log-mdrun-em-solvate-steep   solvate-minimized.gro

Many of the related functions found in the :meth:`common package <amx.base.procedures.common>` operate the same way. They perform generic simulation tasks on a set of files that follow our naming convention outlined in the :doc:`framework <framework>`. The consistent naming scheme makes it easy to apply generic functions to your specific simulation.

You may also note that ``minimize`` calls the :meth:`gmx() <amx.base.gmxwrap.gmx>` function. This function provides the crucial link between the automacs codes and the GROMACS executables run on the command-line. These commands typically have the following form:

.. code-block :: bash
  
  grompp -f input-em-steep-in.mdp -c solvate.gro -o em-solvate-steep.tpr -po solvate.top

The ``gmx`` function wraps all of the GROMACS executables and maps filenames and associated arguments from its ``kwargs`` to the command line. This mapping is set by the ``command_library`` dictionary which is set at the top of the library script. This dictionary ensures that each keyword is correctly mapped to the associated flag for the GROMACS executable. In the example above, the ``top`` keyword maps the ``name`` variable to the ``-po`` flag. This ensures that the topology file (assumed to be ``solvate.top``) is fed directly to the preprocessor. Each procedure has its own specific naming convention defined in the ``command_library``, however these are relatively standardized. 

In the event that the procedure requires more specific interaction with the GROMACS executables, the user may run :meth:`gmx_run() <amx.base.gmxwrap.gmx_run>` to create a custom command line string to be executed by automacs at the appropriate time. Note that both functions ultimate call Python's ``subprocess`` module in order to execute the desired commands at the command line while routing the standard output and error streams to the corresponding log file. These functions use colloquial GROMACS utility names (e.g. "pdb2gmx" or "editconf") which refer to command-line binaries set according to the :doc:`configuration <configuration>`.

In this section we have briefly outlined a "procedure" -- a single, self-contained simulation step which may be a part of a more complex construction procedure. Readers interested in a full example, should consult the TUTORIAL. Each procedure must have a script (e.g. ``amx/procedures/scripts/script-protein.py``) and a corresponding library (in this case, the :meth:`protein_atomistic.py <amx/procedures/protein_atomistic.py>` module). This module should contain functions which are specific to the procedure, however many generic functions apply to many simulations. These can be found in the :meth:`common.py <amx.procedures.common>` module. Finally, the :doc:`controller <controller>` section describes how the procedures are organized and prepared for use.

.. [#wordspace] The ``wordspace`` variable is an overloaded Python dictionary that handles bookkeeping. It keeps track of paths, the simulation topology, etc. The :meth:`init() <amx.base.gmxwrap.init>` function loads the wordspace from the settings block and sometimes implements custom rules.
