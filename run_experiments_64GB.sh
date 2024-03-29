#!/bin/bash

# Define the maximum memory allowed to use (MB)
memorysize=1024

# Define the values for number of hash threads, number of sort threads, and number of write threads
num_threads_hash=(1 4 16)
num_threads_sort=(1 4 16)
num_threads_write=(1 4 16)

# Define the filename
filename="output_experiments_64GB.bin"

# Define the filesize (in MB) 
filesize=65536

# Create an array to store experiment results
experiment_results=()

# Loop through all combinations of parameters
for hash_threads in "${num_threads_hash[@]}"; do
  for sort_threads in "${num_threads_sort[@]}"; do
    for write_threads in "${num_threads_write[@]}"; do
      # Print the current configuration
      echo "Running experiment with hash threads: $hash_threads, sort threads: $sort_threads, write threads: $write_threads"

      # Run the program with the current configuration and capture the output
      output=$(./target/debug/hashgen \
        --t "$hash_threads" \
        --o "$sort_threads" \
        --i "$write_threads" \
        --f "$filename" \
        --m "$memorysize" \
        --s "$filesize")

      # Store the experiment output in the array
      experiment_results+=("$output")
    done
  done
done

# Pass the experiment results to Python for plotting
python3 generate_plots_64GB.py "${experiment_results[@]}"

