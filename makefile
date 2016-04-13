
#---INTERFACE TO CONTROLLER
#-------------------------------------------------------------------------------------------------------------

#---show the banner if no targets
banner:
	@sed -n 1,13p amx/readme.md
	@echo "[NOTE] use 'make help' for details"

#---do not target arguments if using python
.PHONY: banner ${RUN_ARGS}

#---targets
scripts=amx/controller.py
$(shell touch $(scripts))
checkfile=.pipeline_up_to_date

#---filter and evaluate
RUN_ARGS_UNFILTER := $(wordlist 1,$(words $(MAKECMDGOALS)),$(MAKECMDGOALS))
RUN_ARGS := $(filter-out banner help,$(RUN_ARGS_UNFILTER))
$(eval $(RUN_ARGS):;@:)

#---valid function names from the python script
TARGETS := $(shell perl -n -e '@parts = /^def\s+[a-z,_]+/g; $$\ = "\n"; print for @parts;' amx/controller.py amx/procedures/extras/*.py | awk '{print $$2}')

#---hit all of the targets
default: $(checkfile)
$(TARGETS): $(checkfile)

#---exit if target not found
controller_function = $(word 1,$(RUN_ARGS))
ifneq ($(controller_function),)
ifeq ($(filter $(controller_function),$(TARGETS)),)
    $(info [ERROR] "$(controller_function)" is not a valid make target)
    $(info [ERROR] targets are python function names in omni/controller.py or calcs/scripts/*.py)
    $(info [ERROR] valid targets include: $(TARGETS))
    $(error [ERROR] exiting)
endif
endif

#---run the controller
$(checkfile): $(scripts) banner
ifeq (,$(findstring push,${RUN_ARGS}))
	@echo -n "[STATUS] touching: "
	touch $(checkfile)
	@echo "[STATUS] calling controller: python amx/controller.py ${RUN_ARGS} ${MAKEFLAGS}"
	@python amx/controller.py ${RUN_ARGS} ${MAKEFLAGS} && echo "[STATUS] done" || { echo "[STATUS] fail"; }
endif

#---print the readme
help:
ifeq (,$(findstring push,${RUN_ARGS}))
	@echo -n "[STATUS] printing readme: "
	more amx/readme.md
endif
