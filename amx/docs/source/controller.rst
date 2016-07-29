
**********
Controller
**********

In the :doc:`concept <concept>` section, we described the use of :ref:`concept_procedures`, which are self-contained simulation tasks that can be executed in series or parallel. In this section, we will describe the top-level automacs commands which are necessary to execute these procedures. 

.. warning::

	For a complete example of how this works, see the TUTORIALS.

Makefile
########

Users interact with automacs codes with an overloaded ``Makefile`` designed to make it easy to run commands from the terminal without a system-level program installation or the annoying use of ``./executable.sh`` to run commands. Instead, users run commands like `make help` and the `Makefile` routes the commands to a few python scripts in the `amx` folder.

Makefile is standard on linux systems, most of which also have tab-completion. Users can hit ``<tab>`` twice after ``make`` to see many of the utility functions that automacs provides. We will describe these in detail in the remainder of the section.

Overloading the Makefile
************************

Using the ``make`` program allows users to add their own functions to the automacs system. The ``Makefile`` calls any Python function in the global namespace of ``amx/controller.py``, but it also checks any python script found in ``amx/procedures/extras``. We have added an example called :meth:`plot_energy() <amx.procedures.extras.script_energy.plot_energy>` which takes a GROMACS energy file as its only argument. The controller will route all arguments and makefile-compatible keyword definitions into the ``*args`` and ``**kwargs`` of the user-generated python functions. This happens automatically, so that you can write an arbitrary number of extention functions for the controller, each of which will be accessible from the terminal via ``make my_function 10 name=new_name`` which would call a user-defined function.

.. code-block :: python

	def my_function(number,name='default_name'):
		"Do something the user asks..."
		print "I will comply!"

Use ``make`` tab-completion to see which functions are available. In the remainder of this section we will refer to some other controller functions such as ``review`` and ``upload`` which use the makefile-python interface to process user requests.

.. warning :: 

	link the functions above

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

.. warning:: 

	4. POINT TO WORDSPACE.JSON

Supporting codes
****************

The parent scripts for each procedure are designed to be simple and readable. The example parent script in the :ref:`procedures <concept_procedures>` section consists of python functions that use obvious names like ``minimize`` and ``equilibrate``. These functions can be arbitrarily complex, and are stored in python modules within the ``amx/procedures`` folder. 

.. warning::

	link to a definition of parent script or some tutorials or something

Each procedure may have a supporting cast of functions written to a dedicated file in ``amx/procedures``. Recall that python source codes can be easily imported as a module if they exist in a directory with a ``__init__.py``. When a parent script loads automacs modules via ``from amx import *``, it gets the procedure name from the settings block and uses a lookup table found in an internal :meth:`table of contents <amx.procedures>` to locate the correct module. This table points from a procedure name like ``aamd,protein`` to the corresponding module e.g. ``amx/procedures/protein_atomistic.py``. The :doc:`framework <framework>` section outlines the directory structure in more detail. Functions which are specific to a single procedure should be written to that procedure's module file. More general-use functions -- those that can be shared *between* procedures -- should be stored in the ``amx.procedures.common`` module, which is always imported.

Some simulation procedures require only common functions, and hence do not load any additional modules. .....

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

.. _looking:

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

.. _chaining:

Chaining procedures
###################

Automacs allows users to link procedures so that one step receives the result of another. This can be done by running ``make program <next_procedure>`` after the first procedure is completed. A minimal example of this is found in the ``multiply`` procedure, which stacks small simulation boxes on top of each other to create a larger simulation. It effectively wraps the GROMACS `genconf <http://manual.gromacs.org/programs/gmx-genconf.html>`_ utility with the added advantage that it keeps track of the composition of your system so that you don't have to manually write new topology files. 

The ``multiply`` step tells automacs that it is "downstream" of another step by setting ``proceed: true`` in the settings block.

.. literalinclude :: ../../procedures/scripts/script-multiply.py
  :tab-width: 4
  :emphasize-lines: 7,19,21
  :linenos:

The example parent script above also retrieves the last frame of the previous simulation using :meth:`get_last_frame() <amx.procedures.common.get_last_frame>`. This function is used in many places because it fetches the most recent structure from an ongoing simulation trajectory, even if the run did not finish. It relies on :meth:`detect_last() <amx.base.tools.detect_last>` to get the last step folder and part number, which must be stored in ``last_step`` and ``last_part``. Part numbers are explained further in the :doc:`framework <framework>`. The :meth:`resume() <amx.base.functions.resume>` function is responsible for retrieving the checkpoint from the previous step. Upstream steps may save measurements to the wordspace for downstream steps to use.

.. _metarun:

Advanced procedures with "metarun"
##################################

Procedures are the "atomic" unit of automacs execution. Users can prepare and execute these individually or :ref:`chain <chaining>` them together during a single terminal session. We can abstract this once more to create a "metarun", a pre-defined series or batch of procedures that executes without user intervention. Users also have the option to run codes *between* procedure steps which are totally independent of the automacs framework. In the following sections we will describe the features of the typical use cases. 

.. warning::

	link to tutorials first

Metarun scripts are stored in the ``inputs`` folder, which is safe from ``make clean`` and hosts the bundles.

.. warning :: 
	
	link to bundles

A single-procedure metarun
**************************

The metarun functionality can even be useful for a single procedure because it doesn't require the user to alter any settings files. The following script stored at ``inputs/metarun_free.py`` can be used to make a free bilayer.

.. code-block :: python
	:tab-width: 4
	:linenos:

	settings_cgmd_bilayer = """
	system name:        CGMD BILAYER
	lipid structures:   inputs/cgmd-lipid-structures
	step:               bilayer
	procedure:          cgmd,bilayer
	shape:              flat
	lx:                 100
	# more settings ...
	"""

	import sys,os,shutil,subprocess
	execfile('amx/base/metatools.py')

	call('make clean sure')
	call('make program cgmd-bilayer')
	script_settings_replace('script-cgmd-bilayer.py',settings_cgmd_bilayer)
	call('./script-cgmd-bilayer.py')
	subprocess.check_call('./script-continue.sh',cwd='s02-bilayer')

In this metarun script, we use :meth:`call() <amx.base.metatools.call>` to run commands at the terminal and recapitulate the user's actions in a typical procedure. The function ``call('make program cgmd-bilayer')`` will prepare the default script for the user to customize in a text editor. The metarun does this for you.  Before executing the parent script ``script-cgmd-bilayer.py``, the :meth:`script_settings_replace() <amx.base.metatools.script_settings_replace>` function replaces the settings block in the parent script with the one above in the metarun script. By storing your metarun scripts in the ``inputs`` folder, you can create and store many different custom simulation recipes.

Using metarun to make batches of simulations
********************************************

The operation described above is easily extended to generate batches of either identical (that is "replicates") or similar simulations. In the following example, we will create six different benchmarking simulations, each of which uses a different number of nodes (and hence a different total number of processors) on a typical supercomputer.

.. code-block :: python

	#!/usr/bin/python

	import sys,os,shutil,subprocess
	from base.metatools import *

	settings = """
	step:               continueNODESPEC
	system name:        system
	procedure:          continue
	hostname:           gordon
	walltime:           00:30
	nnodes:             NNODES
	"""

	#---loop over number of nodes
	nnodes = [1,2,4,8,10,16]
	batch_submit_script = 'script-batch-submit.sh'

	call('make -s clean sure')
	with open(batch_submit_script,'w') as fp: fp.write('#!/bin/bash\n')
	#---one short run for each number of nodes
	for key in nnodes:
		if os.path.isfile('script-continue.py'): os.remove('script-continue.py')
		call('make -s program continue')
		named_settings = re.sub('NODESPEC','-%dnodes'%key,settings)
		named_settings = re.sub('NNODES','%d'%key,named_settings)
		script_settings_replace('script-continue.py',named_settings)
		#---the continue procedure copies the CPT/TPR files into place and 
		#---...prepares a script-continue.sh
		call('./script-continue.py')
		#---the cluster procedure prepares the cluster script with 
		#---...overrides to machine_configuration
		if os.path.isfile('script-cluster.py'): os.remove('script-cluster.py')
		call('make -s program cluster')
		script_settings_replace('script-cluster.py',named_settings)
		call('./script-cluster.py')
	os.chmod(batch_submit_script,0744)

For each simulation in the batch, the loop uses ``make program continue`` to create a new continuation script. This script copies a preloaded ``CPT`` and ``TPR`` file from the test-case simulation into its own step folder. Note that in contrast to the chaining procedure, these steps are not executed in sequence. Instead, the scripts required to execute each simulation in the batch are logged in a submission script. When the batch is ready, the user can run ``./script-batch-submit.sh`` which will submit all of the simulations to the supercomputer queue all at once. 

Since each supercomputer may have a unique queue, software environment, and rules about runtime, you can set all of these in a central location described in the :doc:`configuration <configuration>` section so that all simulations run on a particular machine comply with the rules for that machine. The batch functionality described in this section is made possible by a simple `regex <https://docs.python.org/2/library/re.html>`_ substitution that sweeps the ``nnodes`` parameter across a number of values.

Using metarun to access external codes
**************************************

Users can access any external python functionality in between steps. The following example is used to place a protein on a coarse-grained bilayer using a set of translations and rotations implemented in an external library.

.. note that the following example depends on the current state of the metarun and may be deprecated as we develop metarun further

.. literalinclude :: ex_metarun_advanced.py
  :tab-width: 4
  :emphasize-lines: 19
  :linenos:

The ``codes`` module imported above is developed and distributed as part of a :ref:`bundle` which can be easily shared. This method for extending automacs makes it possible to automate tasks that users might perform either manually, using other pieces of software, or simply using additional codes. Bundles can be retrieved from a public source (e.g. `GitHub <http://www.github.com>`_) using the controller's ``review`` function.

.. warning ::

	link to a menu of bundles directly instead of github

.. code-block :: bash

	make review source=green:~/path/to/bundle_repo

In this example we are retrieving the bundle from an `ssh-aliased <https://www.freebsd.org/cgi/man.cgi?query=ssh_config&sektion=5>`_ machine, however ``source`` can be a web location or a local path (any valid target for ``git clone``).

Other useful controller functions
#################################

The following commands can be accessed via ``make <command>`` to perform a variety of useful functions.

1. Start from scratch with :meth:`clean <amx.controller.clean>`

.. autosimple:: amx.controller.clean

2. Delete steps with :meth:`delstep <amx.controller.delstep>`

.. autosimple:: amx.controller.delstep

3. Run a program in the background with :meth:`back <amx.controller.back>`

.. autosimple:: amx.controller.back

4. Upload files to a computer cluster with :meth:`upload <amx.controller.upload>`

.. autosimple:: amx.controller.upload

5. Download files from a computer cluster with :meth:`download <amx.controller.download>`

.. autosimple:: amx.controller.download

6. Generate a local hardware/software configuration with :meth:`config <amx.controller.config>`

.. autosimple:: amx.controller.config

7. Write cluster queue submission headers with :meth:`cluster <amx.controller.cluster>`

.. autosimple:: amx.controller.cluster

7. Find a function with :meth:`locate <amx.controller.locate>`

.. autosimple:: amx.controller.locate

The :doc:`configuration <configuration>` section explains the file transfer and supercomputer features in more detail.