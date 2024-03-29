

       d8888 888b     d888 Y88b   d88P 
      d88888 8888b   d8888  Y88b d88P  
     d88P888 88888b.d88888   Y88o88P   
    d88P 888 888Y88888P888    Y888P    
   d88P  888 888 Y888P 888    d888b    
  d88P   888 888  Y8P  888   d88888b   
 d8888888888 888   "   888  d88P Y88b  
d88P     888 888       888 d88P   Y88b 
                                       
    AUTOMACS --- Automatic GROMACS

AUTOMACS (amx) makefile provides the following functions

COMMANDS:

make help.............show this help
make <tab>............show all make targets (if autocomplete)
make docs.............build HTML documentation with sphinx
make program <name>...prepare scripts for a procedure (below)
make config...........set up paths and hardware settings 
                      in ~/.automacs.py
make config local.....set up paths and hardware settings 
                      in ./config.py which overrides ~/.automacs.py
make clean............reset the project by deleting all steps
make cluster..........prepare batch scripts for use on a cluster
make upload...........upload the checkpoint files for an in-progress
                      simulation to a cluster to continue production
make delstep <N>......roll back a step (be careful)
make look.............drop into a shell with the "wordspace"

PROCEDURES:

protein...............prepares scripts for atomistic protein
                      simulations with settings found in
                      script-protein.py which the user should
                      modify before running ./script-protein.py
homology..............build a homology model using MODELLER or
                      or mutate a protein from the PDB
cgmd-bilayer..........a coarse-grained bilayer, possibly with 
                      adhered proteins
multiply..............copy (replicate) a simulation in any of three 
                      directions to build a larger system
modify-parameters.....change MDP parameteters for an ongoing 
                      simulation (try making a custom parameters.py
                      inside inputs)

