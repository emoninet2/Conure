#!/bin/bash
# This script runs start_uix.sh in the background as a daemon

# Run start_uix.sh using nohup so it ignores hangup signals
nohup ./stop_uix.sh > stop_uix.log 2>&1

echo "UIX has been stopped."