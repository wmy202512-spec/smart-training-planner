#!/bin/bash
cd /opt/smart-training-planner
nohup python3 app.py > /tmp/jumpapp.log 2>&1 &
echo $! > /tmp/jumpapp.pid
