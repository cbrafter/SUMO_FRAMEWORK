# Makefile to build docker and run simulations on Linux

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

# Make the docker container
build:
	docker build -t $(VMNAME) .

# Run the script that performs all simulations
runAll: 
	mkdir -p $(RESULTPATH)
	docker run $(DOCKER_ARGS) $(VMNAME) \
		python parallelRun.py $(START) $(END)

# Run the script that performs a special test case
selection:
	mkdir -p $(RESULTPATH)
	docker run $(DOCKER_ARGS) $(VMNAME) \
		python parallelSelection.py $(START) $(END)

# Run the test case to see if docker works
test:
	mkdir -p $(RESULTPATH)
	docker run $(DOCKER_ARGS) $(VMNAME) \
		python dockerTest.py $(START) $(END)

# Docker hello world test
hello_world:
	docker run $(DOCKER_ARGS) $(VMNAME) \
		python -c "print('Hello world :)')"

# Check to see if command args and escaped folder string work 
echo_test:
	echo $(UESCPATH) $(START) $(END)

# delete the docker container completely
# sudo docker images
# sudo docker rmi $REPO_HASH
prune:
	docker system prune
	docker container prune
	docker volume prune
	docker image prune

clean_models:
	rm -rf 2_models/*_*
