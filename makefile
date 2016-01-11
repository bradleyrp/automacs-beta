
#---INTERFACE TO CONTROLLER
#-------------------------------------------------------------------------------------------------------------

#---show the banner if no targets
banner:
	@echo -n "[STATUS] banner via "
	sed -n 1,13p amx/readme.md
	@echo "[NOTE] use 'make help' for details"

#---do not target arguments if using python
.PHONY: banner ${RUN_ARGS}

#---targets
scripts=amx/controller.py
$(shell touch $(scripts))
checkfile=.pipeline_up_to_date

#---filter and evaluate
RUN_ARGS_UNFILTER := $(wordlist 1,$(words $(MAKECMDGOALS)),$(MAKECMDGOALS))
RUN_ARGS := $(filter-out banner docs help scrub,$(RUN_ARGS_UNFILTER))
$(eval $(RUN_ARGS):;@:)

#---valid function names from the python script
TARGETS := $(shell perl -n -e '@parts = /^def\s+[a-z,_]+/g; $$\ = "\n"; print for @parts;' \ amx/controller.py | awk '{print $$2}')

#---hit all of the targets
default: $(checkfile)
$(TARGETS): $(checkfile)

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

#---clean before push
scrub:
	@echo -e "[STATUS] cleaning: "
	rm -f ./amx/docs/build || true
	rm -rf ./config.py || true
	python amx/controller.py clean sure

#---wrap git push
push: scrub
	bash ./amx/base/push.sh ${RUN_ARGS}
	@if [ false ]; then { echo "[STATUS] done"; exit 0; } else true; fi

#---redirect docs to a custom script
docs:
ifeq (,$(findstring push,${RUN_ARGS}))
	@echo -e "[STATUS] building documentation "
	bash amx/docs/source/boostrap_docs.sh ${RUN_ARGS};
	@if [ -d amx/docs/build ]; then { echo "[STATUS] done"; exit 0; } else { bash amx/docs/source/boostrap_docs.sh; } fi
endif
