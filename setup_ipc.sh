#!/bin/bash

# Define the name of the named pipe
IPC_PIPE="/home/manderson240/cohezion/ipc_pipe"

# Create the named pipe if it doesn't exist
if [[ ! -p "$IPC_PIPE" ]]; then
    mkfifo "$IPC_PIPE"
fi

echo "IPC pipe created at $IPC_PIPE"
echo "Starting IPC listener in the background..."
echo "To stop the listener, you can use the 'jobs' command to find the process and 'kill %<job_id>' to stop it."

# Start a background process to read from the pipe and execute commands
while true; do
    if read line < "$IPC_PIPE"; then
        if [ -n "$line" ]; then
            eval "$line"
        fi
    fi
done &

echo "IPC listener started with PID $!"
