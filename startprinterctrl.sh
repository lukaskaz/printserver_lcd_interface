#!/bin/bash
PRINTERLOG=printerctrl.log 

cd /root/printercontroller/
echo -e "---- START on $(date) ----\n" | tee $PRINTERLOG
python3 ./printerctrl.py 2>&1 | tee -a $PRINTERLOG
echo -e "\n----- END on $(date) -----" | tee -a $PRINTERLOG

