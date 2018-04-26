# Makefile to build on Linux

VMNAME = sumovm
ESCPATH = $(shell printf "%q\n" "$(shell pwd)")
UESCPATH = $(shell pwd | sed -e 's/ /\\ /g' -e 's/\[/\\\[/g' -e 's/\]/\\\]/g')
RESULTPATH = /hardmem/results_test/
ROUTEFILEPATH = /hardmem/ROUTEFILES/
DOCKER_ARGS = \
		-v $(RESULTPATH):/hardmem/results/ \
		-v $(UESCPATH)/1_sumoAPI/:/simulation/1_sumoAPI/ \
		-v $(UESCPATH)/2_models/:/simulation/2_models/ \
		-v $(UESCPATH)/3_signalControllers/:/simulation/3_signalControllers/ \
		-v $(UESCPATH)/4_simulation/:/simulation/4_simulation/ \
		-v $(ROUTEFILEPATH):$(ROUTEFILEPATH) \
		-w /simulation/4_simulation
START ?= 1
END ?= 11

build:
	docker build -t $(VMNAME) .

runAll: 
	mkdir -p $(RESULTPATH)
	docker run $(DOCKER_ARGS) $(VMNAME) \
		python parallelRun.py $(START) $(END)

special:
	mkdir -p $(RESULTPATH)
	docker run $(DOCKER_ARGS) $(VMNAME) \
		python ParallelSpecial.py $(START) $(END)

test:
	mkdir -p $(RESULTPATH)
	docker run $(DOCKER_ARGS) $(VMNAME) \
		python dockerTest.py $(START) $(END)


hello_world:
	docker run $(DOCKER_ARGS) $(VMNAME) \
		python -c "print('Hello world :)')"


echo_test:
	echo $(UESCPATH) $(START) $(END)

prune:
	docker system prune
	docker container prune
	docker volume prune
	docker image prune
