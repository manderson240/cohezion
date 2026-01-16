#!/bin/sh
while true; do
  # Log CPU and memory usage of running processes
  ps -eo pid,user,%cpu,%mem,args >> /home/mike-anderson/dev/cohezion/src/diagnostics/process_usage.log
  
  # Wait before next iteration
  sleep 10
done
