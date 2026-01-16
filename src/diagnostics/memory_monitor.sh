#!/bin/sh
while true; do
  # Log current memory usage
  free -h >> /home/mike-anderson/dev/cohezion/src/diagnostics/memory_usage.log
  
  # Log processes sorted by memory usage
  ps aux --sort=-%mem >> /home/mike-anderson/dev/cohezion/src/diagnostics/process_list.log
  
  # Wait before next iteration
  sleep 5
done
