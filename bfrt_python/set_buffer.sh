#!/usr/bin/expect -f
set arg1 [lindex $argv 0]
spawn ssh gomezgaj@10.173.1.211 "edit; set class-of-service schedulers be-scheduler buffer-size temporal $arg1;commit and-quit"
expect "assword:"
send "2\$4FExj9yhmh\$2PX5%2vee\r"
interact
