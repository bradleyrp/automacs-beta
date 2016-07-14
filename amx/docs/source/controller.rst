
**********
Controller
**********

In the :doc:`concept <concept>` section, we described the use of :ref:`concept_procedures`, which are self-contained simulation tasks that can be executed in series or parallel. In this section, we will describe the top-level automacs commands which are necessary to execute these procedures. For a complete example of how this works, see the TUTORIALS.

Makefile
########

Users interact with automacs codes with an overloaded ``Makefile`` designed to make it easy to run commands from the terminal without a system-level program installation or the annoying use of ``./executable.sh`` to run commands. Instead, users run commands like `make help` and the `Makefile` routes the commands to a few python scripts in the `amx` folder.

Makefile is standard on linux systems, most of which also have tab-completion. Users can hit ``<tab>`` twice after ``make`` to see many of the utility functions that automacs provides. We will describe these in detail in the remainder of the section.

Overloading the Makefile
************************

Using the ``make`` program allows users to add their own functions to the automacs system. The ``Makefile`` calls any Python function in the global namespace of ``amx/controller.py``, but it also checks any python script found in ``amx/procedures/extras``. We have added an example called :meth:`plot_energy() <amx.procedures.extras.script_energy.plot_energy>` which takes a GROMACS energy file as its only argument. The controller will route all arguments and makefile-compatible keyword definitions into the ``*args`` and ``**kwargs`` of the user-generated functions.

MORE ADVANCED OVERLOADED MAKEFILE EXAMPLE possibly "make review source=..."

Procedures
##########

Most simple automacs simulations start with a single procedure. Users can begin making a procedure using the following command:

.. code-block :: bash

	$ make program protein
	$ ls
	amx  inputs  makefile  README.md  script-protein.py

This command copies the corresponding script from ``amx/procedures/scripts`` into the root directory. The user can then modify the script (``script-protein.py`` in the example above), and in particular, the settings block at the top of the script, in order to customize the procedure to their specific goal. Once the script is ready, the user can execute it in the usual fashion.

.. code-block :: bash

	$ ./script-protein.py

Procedures follow a standard protocol for preparing and executing the simulation. This always includes the following elements.

1. Create a single folder for the current procedure. In the atomistic protein example, this folder will be named e.g. ``s01-protein`` (the user can customize the name by modifying ``step: <name>`` in the script).
2. Copy the parent script to the step folder for posterity. When running large batches of simulations in parallel, you may make many customized scripts at the parent level, change them, and then execute in the background. Keeping the parent script with the data it generates is a best practice (we follow this convention throughout automacs).
3. Make an automacs-specific log file in the parent directory with the step number and the name of the step e.g. script-s01-protein.log. See the :ref:`log <sec_log>` section below for more details.
4. POINT TO WORDSPACE.JSON

Most (but not all) procedures require a specific library of functions which are automatically loaded by automacs according to a lookup table found in an internal :meth:`table of contents <amx.procedures.toc>`. This table points from a procedure name like ``aamd,protein`` to the corresponding library script e.g. ``amx/procedures/protein_atomistic.py``. The :doc:`framework <framework>` section outlines the directory structure in more detail.

.. _sec_log:

The automacs log
################

Automacs calls many different GROMACS utility functions in the course of constructing a simulation. These files are logged with a consistent naming scheme described further in :doc:`framework <framework>`. In addition, each procedure has a dedicated log file that will tell you what automacs has done to construct the simulation. This log file also doubles as an instruction set for reproducing the data "manually". That is, every GROMACS command is explicitly recorded so that users can reproduce the simulation in the usual way, by entering a series of GROMACS commands. Since automacs also copies files, the internal automacs functions (e.g. :meth:`filecopy() <amx.base.functions.filecopy>`) are also logged.

Here is an example log-file entry.

.. code-block :: python

	[FUNCTION] gmx ('mdrun',) {'base': 'em-vacuum-steep', 'log': 'mdrun-vacuum-steep'}
	[FUNCTION] gmx_run ('gmx mdrun -nb auto -e em-vacuum-steep.edr \
		-g em-vacuum-steep.log -c em-vacuum-steep.gro -o em-vacuum-steep.trr \
		-v  -s em-vacuum-steep.tpr -x em-vacuum-steep.xtc -cpo em-vacuum-steep.cpt ',) \
		{'skip': False, 'log': 'mdrun-vacuum-steep', 'inpipe': None}

Each ``[FUNCTION]`` entry in the log names a python function along with its ``*args`` and ``**kwargs`` in Python syntax (parentheses for arguments and braces for keyword arguments). Each entry therefore corresponds to a function call within Python. Within the automacs code itself, a `decorator <https://en.wikipedia.org/wiki/Decorator_pattern>`_ named :meth:`@narrate <amx.base.journal>` tells the program to record the function call in the log. Most functions are decorated in this way, so that the user has a complete record of how the simulation was created.

In the example log text above, you can see the typical process by which GROMACS functions are called from the automacs procedure. The originating script calls :meth:`gmx() <amx.base.gmxwrap.gmx` via ``gmx('mdrun',base='em-vacuum-steep',log='mdrun-vacuum-steep')`` and automacs maps the necessary arguments onto GROMACS-style flags. The resulting command is passed to :meth:`gmx_run() <amx.base.gmxwrap.gmx_run>`, which executes it using Python's ``subprocess`` module. This step also routes standard output and error streams into the appropriate log file, named ``log-mdrun-vacuum-steep``. Note that we always prepend ``log-`` to the log argument. This is an example of a file naming convention, more of which can be found in the :doc:`framework <framework>` section.

Each line in the log file is identified by a token e.g. ``[FUNCTION]``. Other tokens include ``[TRACEBACK]`` and ``[ERROR]``, which record Python exceptions and errors for later troubleshooting. Lastly, the ``[CHECKPOINT]`` token serves a special role. It holds the current state of  the ``wordspace`` for subsequent procedures to retrieve. If any procedure outputs, like a free bilayer or an equilibrated protein structure, are required as inputs for additional procedures, they can use the checkpoint to get key attributes of the preceding simulation. When creating a procedure script, you can use the :meth:`checkpoint() <amx.base.gmxwrap.checkpoint>` function to save the wordspace at critical junctures. If you lose track of a function, you can always find it with a :ref:`simple search <finding_functions>`.

"Looking" at the state of your simulation
#########################################

Sometimes it is useful to view the wordspace from inside an interactive Python terminal. To do this, you can run ``make look``, and as long as you have a checkpoint in the log file for the most recently executed step, it will open an interactive Python session. There you can inspect the simulation settings. This usually includes all of the settings defined in the parent script, it also contains readouts that the automacs functions save for later.

.. code-block :: python

	>>> wordspace.step
	u's01-bilayer/'
	>>> print wordspace.composition
	[[u'DOPC', 230], [u'DOPS', 58]]
	>>> wordspace['bilayer_dimensions_slab']
	[14.386, 14.414, 6.31]

Note that the wordspace is an overloaded class, so you can access its members either directly or with Python's dictionary syntax shown above. See the :ref:`wordspace specification <wordspace>` for more details.

Chaining procedures
###################

Automacs allows users to link together procedures so that one step receives the result of another. A minimal example of this is found in the ``multiply`` procedure, which stacks small simulation boxes on top of each other to create a larger simulation. It effectively wraps the GROMACS ``genconf`` LINK!!! utility with the added advantage that it keeps track of the composition of your system so that you don't have to manually write new topology files. 

The ``multiply`` step tells automacs that it is "downstream" of another step by setting ``proceed: true`` in the settings blocks.

.. literalinclude :: ../../procedures/scripts/script-multiply.py
  :tab-width: 4
  :emphasize-lines: 7,19,21
  :linenos:

The example parent script above also retrieves the last frame of the previous simulation using :meth:`get_last_frame() <amx.procedures.common.get_last_frame>` which itself relies on :meth:`detect_last() <amx.base.tools.detect_last>` to get the last step folder and part number.

Advanced procedures with "metarun"
##################################

automate the above

Other controller functions
##########################

1. clean
2. delstep
2. upload/download/cluster
2. back
3. config
5. review
4. watch????
