#!/bin/sh
capacity=1000
rate=`/root/bf-sde-9.2.0/./run_bfshell.sh -f /home/adaptive_buffer_tuning/bfrt_python/link_utilization | tail -6 | head -1 | awk -F '|' '{print $9}' | tr -d " \t"`

if [ ! -z "$rate" ]; then 
	util=`echo "$rate / $capacity" | bc -l`
	echo $util
else
	echo "0"
fi