SDE := /root/bf-sde-9.4.0
DIR := /home/p4bs
PROGRAM := p4bs
LINKS_FILE := ucli_cmds
MEASUREMENTS_FILE := measurements.py

compile:
	cd $(SDE) ; sh . ../tools/./set_sde.bash
	~/tools/p4_build.sh --with-p4c=bf-p4c $(DIR)/p4src/$(PROGRAM).p4

run:
	pkill switchd 2> /dev/null ; cd $(SDE) ;./run_switchd.sh -p $(PROGRAM)

links:
	cd $(SDE) ; ./run_bfshell.sh --no-status-srv -f $(DIR)/$(LINKS_FILE)

measurements:
	$(SDE)/./run_bfshell.sh --no-status-srv -i -b $(DIR)/bfrt_python/$(MEASUREMENTS_FILE)
	
BO:
	python3.9 -W ignore BO_resetting/main.py
