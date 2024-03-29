# Makefile for running experiments and generating plots

# Define targets
.PHONY: all run_experiments generate_plots clean

# Default target
all: run_experiments generate_plots

# Target to run experiments
run_experiments:
        cargo build
        chmod +x run_experiments.sh
        chmod +x run_experiments_64GB.sh
	./run_experiments.sh
	./run_experiments_64GB.sh
	cargo run --release -- --f output_64GBfile_m1024MB --t 4 --o 4 --i 16 --s 65536 --m 1024
	cargo run --release -- --f output_64GBfile_m8192MB --t 4 --o 4 --i 16 --s 65536 --m 8192
	cargo run --release -- --f output_64GBfile_m32768MB --t 4 --o 4 --i 16 --s 65536 --m 32768


# Target to clean up
clean:
	# Clean up any generated files or artifacts

