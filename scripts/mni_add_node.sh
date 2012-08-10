#!/bin/bash

set -u

NODE_NAME=""

while [ -z "$NODE_NAME" ]; do
	read -p "What is the name of this node (e.g rs): " NODE_NAME
done

while true; do
	read -p "What is the IP of this node: " NODE_IP
	NODE_IP=`gethostip -d $NODE_IP`
	if [ $? -eq 0 ]; then break; fi
done

set -x
sudo /usr/bin/dgrp/config/dgrp_cfg_node init -v -v -e never $NODE_NAME $NODE_IP 1 > /dev/null && sleep 1
set +x
TTY_NAME="/dev/tty/${NODE_NAME}00"
if [ -e "$TTY_NAME" ]; then
	if ! [[ -r "$TTY_NAME" && -w "$TTY_NAME" ]]; then
		echo "ERR: Current user does not have read/write permissions"
		echo "on $TTY_NAME"
		echo "Consider fixing your udev rule by appending:"
		echo -e '\tGROUP="dialout'
		echo "Also ensure that the current user is a member of the"
		echo "dailout group (or any other group of your choice)"
		echo
		read -p "Would you like to fixup $TTY_NAME now? [Y/n]" resp
		if [ echo ${resp:0:1} | tr [:lower:] [:upper:] == "N" ]; then
			echo "WARN: You will need to fix this before attempting to use this node"
			echo "Continuing on..."
		else
			set -x
			sudo chgrp dialout "$TTY_NAME"
			sudo chmod g+rwx "$TTY_NAME"
			set +x
		fi
	fi
else
	echo "ERR: Device $TTY_NAME was not created"
	exit 1
fi

if [ -w "config.ini" ]; then
	while true; do
		read -p "config.ini found, add this node? (default Y): " yn
		if [ -z $yn ]; then break; fi
		case $yn in
			[Yy]* ) break;;
			[Nn]* ) exit;;
			* ) echo "Please answer yes or no.";;
		esac
	done

	NUM_NODES=`grep numNodes: config.ini | awk '{n = substr($0, match($0, /[0-9]+/), RLENGTH) + 1; sub(/[0-9]+/, n); print }'`
	NODE_NUMBER=`grep '\[Node[0-9]*\]' config.ini | tail -n 1 | awk '{n = substr($0, match($0, /[0-9]+/), RLENGTH) + 1; sub(/[0-9]+/, n); print }'`
	NODE_ID=`grep 'id:' config.ini | tail -n 1 | awk '{n = substr($0, match($0, /[0-9]+/), RLENGTH) + 1; sub(/[0-9]+/, n); print }'`
	if [ `grep installCmd config.ini | uniq | wc -l` -gt 1 ]; then
		echo "Ambiguous installCmd, cannot auto-add - failing..."
		exit
	fi
	NODE_CMD=`grep installCmd config.ini | uniq`
	read -p "Select 'timeoffset' (default 0): " NODE_TIME
	if [ -z "$NODE_TIME" ]; then NODE_TIME=0; fi

	sed -i "s/`grep numNodes: config.ini`/$NUM_NODES/" config.ini
	sed -i '$ d' config.ini
	echo -ne "$NODE_NUMBER\n$NODE_ID\nip: $NODE_IP\n" >> config.ini
	echo -ne "serial: /dev/tty"$NODE_NAME"00\n" >> config.ini
	echo -ne "$NODE_CMD\ntimeoffset: $NODE_TIME\n" >> config.ini
	echo -ne "\n\n" >> config.ini

	echo "   * $NODE_NUMBER Added to config.ini"
fi
