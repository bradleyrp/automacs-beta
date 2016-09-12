.. amx documentation master file, created by
   sphinx-quickstart on Fri Oct 30 11:37:21 2015.
   You can adapt this file completely to your liking, but it should at least
   contain the root `toctree` directive.

AUTOMACS documentation
======================

AUTOMACS means "automatic GROMACS". These codes are designed to create large batches of biophysical simulations using the popular `GROMACS <http://www.gromacs.org/>`_ integrator, with a particular emphasis on flexible, reproducible simulation routines which are readable and easy to share and distribute. This project was jointly developed by Joe Jordan and Ryan Bradley, PhD students advised by Ravi Radhakrishnan, and serves as a formal effort to "get in-house codes out of the house." We hope that our efforts will make our research more accessible to the scientific community at large.

.. toctree::
  :maxdepth: 4
  :numbered:

  concept
  controller
  framework
  equilibration
  configuration
  tutorials

Codebase
========

Most of the functions in amx sub-modules are designed to be hidden from the user. Instead, these codes document the procedures very explicitly, and these procedure codes should produce documentation for reproducing any simulation procedure while being relatively easy to read.

Check out the :doc:`AMX codebase <amx>` for more details.
