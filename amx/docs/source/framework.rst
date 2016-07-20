
.. title :: Framework

*********
Framework
*********

.. _finding_functions:

Finding functions
-----------------

The authors frequently forget where some functions are found. This is a natural consequence of the automacs modular design in which many functions can be reused for multiple simulation procedures. A quick way to find a function within one of the automacs libraries is to search the directory with one of the following commands:

.. code-block :: bash

	$ grep "def build_bilayer" * -R
	$ find ./ -name "*.py" | xargs grep --color=always "def build_bilayer"

The latter avoids searching large files. 

.. _wordspace:

Wordspace
---------

Under construction