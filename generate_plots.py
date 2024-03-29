import matplotlib.pyplot as plt

def extract_experiment_info(experiment_output):
    # Split the experiment output by whitespace
    parts = experiment_output.split()

    # Extract experiment name (first three terms)
    experiment_name = " ".join(parts[:3])

    # Extract time taken, hashing rate, and processing speed
    time_taken = float(parts[5].rstrip('s'))
    hashing_rate = float(parts[6])
    processing_speed = float(parts[7])

    return experiment_name, time_taken, hashing_rate, processing_speed

def plot_experiment_results(experiment_results):
    # Extract experiment information from each result
    experiment_names = []
    times_taken = []
    hashing_rates = []
    processing_speeds = []

    for result in experiment_results:
        name, time, rate, speed = extract_experiment_info(result)
        experiment_names.append(name)
        times_taken.append(time)
        hashing_rates.append(rate)
        processing_speeds.append(speed)

    # Plot 1: Experiment name vs. Time taken
    plt.figure(figsize=(10, 5))
    plt.plot(experiment_names, times_taken, marker='o')
    plt.title('Experiment Name vs. Time Taken')
    plt.xlabel('Experiment Name')
    plt.ylabel('Time Taken (seconds)')
    plt.xticks(rotation=45)
    plt.tight_layout()
    plt.savefig('experiment_time.png')
    plt.show()

    # Plot 2: Experiment name vs. Hashing rate
    plt.figure(figsize=(10, 5))
    plt.plot(experiment_names, hashing_rates, marker='o')
    plt.title('Experiment Name vs. Hashing Rate')
    plt.xlabel('Experiment Name')
    plt.ylabel('Hashing Rate')
    plt.xticks(rotation=45)
    plt.tight_layout()
    plt.savefig('experiment_hashing_rate.png')
    plt.show()

    # Plot 3: Experiment name vs. Processing speed
    plt.figure(figsize=(10, 5))
    plt.plot(experiment_names, processing_speeds, marker='o')
    plt.title('Experiment Name vs. Processing Speed')
    plt.xlabel('Experiment Name')
    plt.ylabel('Processing Speed')
    plt.xticks(rotation=45)
    plt.tight_layout()
    plt.savefig('experiment_processing_speed.png')
    plt.show()

if __name__ == '__main__':
    import sys
    # Retrieve experiment results from command line arguments
    experiment_results = sys.argv[1:]

    # Plot experiment results
    plot_experiment_results(experiment_results)

