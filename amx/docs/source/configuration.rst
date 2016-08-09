
.. title :: Configuration

*************
Configuration
*************

Every time automacs is executed, it checks for a configuration file to tell it how to execute GROMACS on the host. It looks in two places for the configuration file: either locally at ``config.py`` or in a hidden file in the home directory found at ``~/.automacs.py``. The latter option is the default.

.. warning ::

	Running any automacs command via ``make`` without requesting a local configuration will cause automacs to write the default configuration to ``~/.automacs.py``. You can pre-empt this by running ``make config local`` before running any other commands. If automacs finds ``~/.automacs.py`` it will use it.

The purpose of this configuration file is to specify the version of gromacs and the hardware configuration for each machine that uses automacs. Once you customize the global configuration file at ``~/.automacs.py`` for a particular machine, all subsequent automacs simulations will use that configuration. This means that quirky names for GROMACS binaries e.g. ``mdrun_mpi_d`` only need to be described once. 

Moreover, if you wish to use alternate versions of GROMACS or alternate hardware configurations on some simulations, but not others, you may customize a ``config.py`` in each of the unique simulations. The ``config.py`` file will follow the data if you use the :meth:`upload <amx.controller.upload>` functionality. The configuration file is also useful for deploying automacs simulations on supercomputing resources. The configuration file can tell automacs how to submit your jobs to the queue. In the following sections we will describe how to set up the configuration. 

Quickstart
----------

If you plan to run automacs locally (i.e. without a batch submission system) and you already have GROMACS binaries in your path, you don't need to do anything. Automacs will create a global configuration file at ``~/.automacs.py`` which contains a dictionary called ``machine_configuration``. Users who do not customize this dictionary will use the overrides found in the (empty) ``LOCAL`` dictionary. Any settings described below can be added to the ``LOCAL`` dictionary to be used as the default.


Host-specific configurations
----------------------------

The ``machine_configuration`` dictionary holds host-specific configurations. You can populate and maintain a single, custom ``~/.automacs.py`` for use on all of your machines so that you don't have to worry about setting the software or hardware environment on new simulations on those machines. The keys in ``machine_configuration`` are matched to the system's hostname (via ``os.environ['HOSTNAME']``). You can use regular expressions in the keys if you wish (the matchin happens via Python's `re.search <https://docs.python.org/2/library/re.html>`_). If a match is found, automacs uses the settings in the corresponding sub-dictionary. Otherwise it uses the ``LOCAL`` subdictionary.

.. note ::

	With version 5, GROMACS changed the names of many of its executables to declutter the path. For example, ``trjconv`` in version 4 became ``gmx convert-tpr`` in version 5. Many of the version 5 utilities are accessed via a single executable called ``gmx``. The automacs code will automatically detect your GROMACS version series (either 4 or 5) by probing the terminal. When using environment modules :ref:`described below <modules>` you can override the series number using ``gmx_series`` if neccessary.

The settings sub-dictionaries can contain the following entries.

1. Setting ``nprocs`` will tell GROMACS how many threads to use. Note that this uses the built-in threading (not MPI).
2. Use the ``gpu_flag`` setting to tell GROMACS whether to use a GPU (if possible). This option is passed directly to the ``-nb`` flag for ``mdrun`` and hence can be one of the following: ``auto``, ``cpu``, ``cpu_gpu``. 
3. Setting the ``suffix`` key will append a string to every GROMACS binary. This is useful on systems where you have compiled different versions of GROMACS with e.g. MPI support to names like ``mdrun_mpi`` or double-precision versions named via ``mdrun_d``.
4. Some systems, particularly those that use MPI, require a custom ``mdrun`` command which you can set via ``mdrun_command``. This allows users to specify an MPI executable which wraps the ``mdrun`` command. A common useage follows this form: ``mpirun_rsh -np 16 mdrun_mpi``. Whenever automacs needs the ``mdrun`` executable, it will use this command instead.

The settings sub-dictionaries are extremely flexible. In the following sections we will describe how to use these dictionaries to use environment modules and queueing systems common to many supercomputing platforms.

Batch submission
----------------

Most simulations are run on large supercomputing platforms that require users to submit jobs to a queueing system. Automacs can prepare a custom submission script using the configuration file and the :meth:`cluster <amx.controller.cluster>` function. Users should add text blocks containing the general format for the header on the submission script. We have included several examples in the default configuration (which can be found at ``amx/base/default_config.py``). 

The cluster header text for a particular hostname should be referred by variable name inside of the settings sub-dictionary. Any capitalized words in the cluster header will be replaced by values in the sub-dictionary if a match is found. For example, if you include ``ALLOCATION`` in your cluster header, and then set the ``allocation`` key in the settings, then automacs will fill in the allocation code whenever it writes a cluster submission script. This happens when the user runs ``make cluster``. This also works for other variables e.g. ``WALLTIME``.

Automacs will also compute the total number of processors from the ``ppn`` and ``nnodes`` settings which correspond to the number of processors per node and the number of nodes, respectively. This value is implicitly added to the settings variable ``nprocs`` which is then substituted for ``NPROCS`` in the cluster header. This particular variable also gets set as a BASH variable in the cluster script so you can use ``$NPROCS`` in your ``mdrun_command``. 

Additionally, the ``walltime`` variable from ``machine_configuration`` to the cluster submission header, we also convert it from e.g. ``24:00:00`` into hours for the ``mdrun -maxh`` flag, which will gently stop your simulation and write a final configuration shortly before time expires. The :meth:`cluster <amx.controller.cluster>` function writes a standardized BASH script stored at ``amx/procedures/scripts/scripts-continue.sh`` with these custom values. Users may also set the total simulation time or extension time in nanoseconds by sending the ``extend`` or ``until`` settings to the :meth:`write_continue_script <amx.base.functions.write_continue_script>` function inside of their parent script.

.. warning::

	Fix repeated code in cluster and write_continue_script

The ``mdrun_command`` is interpreted by BASH inside of the cluster submission script. This allows you to use a custom call that includes MPI settings as well as the number of processors computed from ``ppn`` and ``nnodes``.

.. code-block :: bash

	$(echo "mpirun_rsh -np $NPROCS -hostfile $PBS_NODEFILE GMX_ALLOW_CPT_MISMATCH=1 $(which mdrun_mpi)")

.. _modules:

Modules
-------

If the GROMACS binaries are already available in your path, then automacs will have no trouble finding them. However, many supercomputing platforms and even individual users prefer to compile several versions of GROMACS using a program called `environment modules <http://modules.sourceforge.net/>`_. Automacs is designed to interact with the modules program to load a specific version of GROMACS for any simulation.

Typically, users load software modules by running a command such as ``module load gromacs/4.6.3``. Automacs will do this for you if you populate the ``modules`` keyword in your ``machine_configuration`` with a single string or a list of strings corresponding to available modules. You can check the correct software names using ``module avail`` as long as environment modules is installed.

.. note::

	Automacs interacts with the environment modules package by using a header file which is typically located at ``/usr/share/Modules/default/init/python.py``. If you install the modules package to a different location, you should include the path to your ``python.py`` as the ``modules_path`` variable in the ``machine_configuration``. Note that systems running python versions before ``2.7`` will attempt to load modules directly from the terminal because these versions of python lack the ``importlib`` library necessary to communicate with other packages.

In addition to loading the correct modules before local execution, automacs also adds them to any cluster submission scripts that it writes. 

.. note::

	If you wish to use specific GROMACS versions for some simulations, we recommend customizing the ``config.py`` file which is created by running ``make config local``. This file overrides the global version at ``~/.automacs.py``.
