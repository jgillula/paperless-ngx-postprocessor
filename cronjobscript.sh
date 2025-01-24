#!/bin/bash
ps -eaf | grep -i "paperlessngx_postprocessor.py" | grep -v grep
# if not found - equals to 1, start it
if [ $? -eq 1 ]
then
#echo "eq 0 - paperlessngx_postprocessor not running"
printenv
/usr/src/paperless/scripts/venv/bin/python3 /usr/src/paperless/scripts/paperlessngx_postprocessor.py --verbose DEBUG process --tag auto-
else
echo "eq 0 - paperlessngx_postprocessor running - do nothing"
fi