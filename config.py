#!/usr/bin/python

"""
AUTOMACS configuration file
machine_configuration tells AUTOMACS how to run GROMACS
the `LOCAL` entry is used by default
missing entries are simply omitted from GROMACS commands
the gpu_flag is passed to GROMACS via "mdrun -nb <gpu_flag>"
additional entries are used to configure remote machines
they will be used if the key is a substring in the hostname
modules is a comma-separated list of modules to load
otherwise the GROMACS executables must be in the path
you may also supply a cluster_header for use on TORQUE clusters
any keys in the entry will overwrite uppercase keys in the header
"""

#---a typical cluster header
compbio_cluster_header = """#!/bin/bash
#PBS -l nodes=NNODES:ppn=NPROCS,walltime=WALLTIME:00:00
#PBS -j eo 
#PBS -q opterons
#PBS -N gmxjob
echo "Job started on `hostname` at `date`"
cd $PBS_O_WORKDIR
#---commands follow
"""

machine_configuration = {
	'LOCAL':dict(),
	'compbio':dict(
		nnodes = 1,
		nprocs = 16,
		gpu_flag = 'auto',
		modules = 'gromacs/gromacs-4.6.3',
		cluster_header = compbio_cluster_header,
		walltime = 24,
		),
	}
