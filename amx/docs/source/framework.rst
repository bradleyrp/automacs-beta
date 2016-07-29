
.. title :: Framework

*********
Framework
*********

.. warning ::

	need to open this section with a brief overview

.. _directory_structure:

File-naming structure
=====================

Directories
-----------

In order to ensure that automacs procedures can be re-used in many different situations, we enforce a consistent directory structure. This makes it easy for users to write shorter codes which infer the location of previous files without elaborate control statements. The basic rule is that each procedure gets a separate folder, and that subsequent procedures can find input data from the previous procedure folder. 

We find it hard to imagine that users would chain more than 99 steps together, so we name each step with a common convention that includes the step number e.g. ``s01-bilayer`` and ``s02-large-bilayer`` etc. Many automacs functions rely on this naming structure. For example :meth:`delstep <amx.controller.delstep>` allows you to delete the most recent step and start it over again. The :meth:`upload <amx.controller.upload>` function is designed to send only your latest checkpoint to a supercomputer to continue a simulation. The :meth:`get_last_frame <amx.base.functions.get_last_frame>` function will retrieve the last valid frame from a running trajectory to serve as the input for any subsequent procedures. This function is essential to the :ref:`chaining <chaining>` method described earlier.

The step name
-------------

The step name is always provided by the ``step`` variable in the parent script settings block. To create the directory, each parent script must first include ``init(settings)`` to load the settings into the wordspace (described further :ref:`below <wordspace>`) followed by the :meth:`start <amx.base.functions.start>` function via ``start(wordspace.step)`` which creates a new directory and also copies files and directories according to :ref:`retrieval <retrieval>` rules in the settings block.

.. _file_names:

Files
-----

Within each procedure directory, we also enforce a file naming scheme that reflects much of the underlying GROMACS conventions. In particular, when simulations are extended across multiple executions, we follow the ``md.part0001.xtc`` numbering rules. Every time the ``mdrun`` integrator is invoked, automacs writes individual trajectory, input binary, and checkpoint files. Where possible, it also writes a configuration file at the conclusion of each run. 

When we construct new simulations, we also follow a looser set of rules that makes it easy to see how the simulations were built.

1. All GROMACS output to standard output and standard errors streams (that is, written to the terminal) is captured and stored in files prefixed with ``log-<gromacs_binary>``. In this case we label the log file with the gromacs utility function used to generate it. Since many of these functions are called several times, we also use a name for that part of the procedure. For example, during bilayer construction, the file ``s01-bilayer/log-grompp-solvate-steep`` holds the preprocessor output for the steepest descent minimization of the water-solvated structure. 
2. While output streams are routed to log files, the formal outputs from the GROMACS utilities are suffixed with a name that corresponds to their portion of the construction procedure. We use the prefix ``em`` to denote energy minimization and ``md`` to denote molecular dynamics. For example, minimizing a protein in vaccuum might output files such as ``em-vacuum.tpr`` while the NVT equilibration step might be labelled ``md-nvt.xtc``. 
3. Intermediate steps that do not involve minimization or dynamics are typically prefixed with a consistent name. For example, when adding water to a protein or a bilayer, automacs will generate several intermediate structures, all prefixed with the word "solvate" e.g. ``solvate-dense.gro``.

.. _retrieval:

Fetching input files
--------------------

To load each step with necessary input files, the :ref:`start <amx.base.functions.start>` function will copy files and directories. Specify directories in a settings list called ``sources``. To copy individual files to the current step, populate the ``files`` variable. Both should use Python syntax.

.. _wordspace:

Wordspace
=========

In order to transmit key settings and measurements between simulation procedure steps or within functions in the same procedure, we store them in an overloaded dictionary called the "wordspace". In addition to the standard dictionary functions, the wordspace returns ``None`` on dictionary lookups if the key cannot be found. All dictionary items are also elevated to class members so that users can access them with the dot operator for brevity. For example ``wordspace['bilayer_thickness']`` and ``wordspace.bilayer_thickness`` would return the same result. If that key doesn't exist, the former returns ``None`` while the latter raises an exception. These different behaviors are useful for some simulation procedures. Recall that any settings in the settings block for a procedure should be passed to the :meth:`init <amx.base.gmxwrap.init>` function so that they are stored in the wordspace. All spaces in the keys are replaced with underscores.

Checkpoints and chaining
------------------------

The wordspace is available to any library loaded by automacs. More importantly, it can be stored in the automacs log using the :meth:`checkpoint <amx.base.gmxwrap.checkpoint>` function. The corresponding :meth:`resume <amx.base.functions.resume>` function can retrieve the wordspace from a checkpoint written in a previous procedure, thereby making the wordspace available to any downstream steps. This is useful for chaining procedures together.

Incremental development
-----------------------

In the description above, we noted that the parent script starts with :meth:`init <amx.base.gmxwrap.init>` and :meth:`start <amx.base.functions.start>` in order to populate the wordspace and create a new directory with the correct input files. As users develop new procedures, it is often useful to resume a simulation which has failed for some reason. This is made possible by using a try-except loop. Exceptions handled by the custom :meth:`exception_handler <amx.base.metatools.exception_handler>` will write the wordspace to ``wordspace.json`` in the simulation root folder. Each time the parent script is run, it checks for this file. If if finds it, it loads it into the wordspace, and sets the flag ``under_development``. Users who wish to resume an ongoing procedure can use the ``wordspace.under_development`` flag to skip parts of the procedure that have been successfully completed and resume at the site of the previous exception. This obviates the need to repeat successful parts of a simulation when working on subsequent parts of the procedure.

Most incremental development schemes require that the user alters key variables in the wordspace. There are two ways to do this. First, if you continue a procedure after an exception, you can change a setting in the settings block, and be sure that it propagates to the wordspace by running ``init(settings)``. This function must always be executed. You can also manually change the wordspace by using the :ref:`make look <looking>` command in the interactive Python prompt. When you are finished, you can save the change in the automacs log using the :meth:`checkpoint() <amx.base.gmxwrap.checkpoint>` function. If you plan to resume a simulation from ``wordspace.json``, you should write the change there by running :meth:`write_wordspace(wordspace) <amx.base.metatools.write_wordspace>`.

.. warning :: 

	refer to try-except in the protein tutorial

Useful tips
===========

.. _finding_functions:

Finding functions
-----------------

The authors frequently forget where some functions are found. This is a natural consequence of the automacs modular design in which many functions can be reused for multiple simulation procedures. A quick way to find a function within one of the automacs libraries is to search the directory with :meth:`locate <amx.controller.locate>` invoked by ``make locate <function_name>`` which also accepts regular expressions.

Keeping things simple
---------------------

In this section we have described how automacs organizes files. In general the file-naming rules are not absolute requirements for the simulations to complete. Instead, these "rules" have two purposes. First, if you use highly consistent and descriptive naming schemes, then you can easily re-use code in new situations. For example, many of the automacs procedures were developed for atomistic simulations. A few simple name changes along with some extra input files are oftentimes enough to port these procedures to coarse-grained systems or develop more complicated simulations.

The second purpose of our elaborate-yet-consistent naming scheme is to ensure that the data you produce are durable. Carefuly naming can ensure that future users who wish to study your data will not require an excessive amount of training to understand what it holds. An obvious naming scheme makes it easy to share data, find old simulations, and more importantly, parse the data with analysis programs once the dataset is complete. The `omnicalc <http://github.com/bradleyrp/omnicalc>`_ analysis package is designed to process data prepared by automacs, and these file-naming rules make it easy for these programs to be used together.
