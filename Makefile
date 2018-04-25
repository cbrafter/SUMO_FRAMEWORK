# Makefile to build on Linux

VMNAME = sumovm
ESCPATH = $(shell printf "%q\n" "$(shell pwd)")
UESCPATH = $(shell pwd | sed -e 's/ /\\ /g' -e 's/\[/\\\[/g' -e 's/\]/\\\]/g')
START ?= 1
END ?= 11

build:
	docker build -t $(VMNAME) .

ubuntu: 
	docker run \
		-v /hardmem/results_BHAM/:/hardmem/results/ \
		-v $(UESCPATH)/1_sumoAPI/:/simulation/1_sumoAPI/ \
		-v $(UESCPATH)/2_models/:/simulation/2_models/ \
		-v $(UESCPATH)/3_signalControllers/:/simulation/3_signalControllers/ \
		-v $(UESCPATH)/4_simulation/:/simulation/4_simulation/ \
		-w /simulation/4_simulation \
		$(VMNAME) python parallelRun.py $(START) $(END)

ubuntu_special:
	docker run \
		-v /hardmem/results_BHAM/:/hardmem/results/ \
		-v $(UESCPATH)/1_sumoAPI/:/simulation/1_sumoAPI/ \
		-v $(UESCPATH)/2_models/:/simulation/2_models/ \
		-v $(UESCPATH)/3_signalControllers/:/simulation/3_signalControllers/ \
		-v $(UESCPATH)/4_simulation/:/simulation/4_simulation/ \
		-w /simulation/4_simulation \
		$(VMNAME) python ParallelSpecial.py $(START) $(END)

ubuntu_simple:
	docker run \
		-v /hardmem/results_test/:/hardmem/results/ \
		-v $(UESCPATH)/1_sumoAPI/:/simulation/1_sumoAPI/ \
		-v $(UESCPATH)/2_models/:/simulation/2_models/ \
		-v $(UESCPATH)/3_signalControllers/:/simulation/3_signalControllers/ \
		-v $(UESCPATH)/4_simulation/:/simulation/4_simulation/ \
		-w /simulation/4_simulation \
		$(VMNAME) python simpleTest.py

echo_test:
	echo $(UESCPATH)

prune:
	docker system prune
	docker container prune
	docker volume prune
	docker image prune
