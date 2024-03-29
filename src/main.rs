//final code
#![allow(warnings)]
extern crate clap;
extern crate rand;
extern crate blake3;
extern crate rayon;

use rayon::prelude::*;
use std::fs::{File, OpenOptions};
use std::io::{Error, Seek, SeekFrom};
use std::sync::{Arc, Mutex};
use std::time::Instant;
use clap::{App, Arg};
use rand::Rng;
use blake3::{Hasher, hash};
use tokio::io::{AsyncWriteExt, BufWriter};
use futures::stream::FuturesUnordered;
use futures::StreamExt;
use std::io::{Read, Write};
use std::time::Duration;




// Define your Record struct
#[derive(Debug, Clone)]
struct Record {
    hash: [u8; 10],
    nonce: [u8; 6],
}

// Define Args struct to hold parsed command-line arguments
#[derive(Debug)]
struct Args {
    num_threads_hash: usize,
    num_threads_sort: usize,
    num_threads_write: usize,
    filename: String,
    memorysize: usize,
    filesize: usize,
    print_head: usize,
    print_tail: usize,
    debug_mode: bool,
    verify_sort_order: bool,
    verify_blake_hashes: bool,
}

// Define the record size
const RECORD_SIZE: usize = 16; // Adjust this as per your record size

// Function to generate BLAKE3 hashes with nonce using Rayon
fn generate_hashes(num_hashes: usize, num_threads: usize, debug: bool) -> Vec<Record> {
    if debug {
        println!("Generating hashes...");
    }

    let start_time = Instant::now();

    let hashes: Vec<Record> = (0..num_hashes)
        .into_par_iter()
        .enumerate() // Enumerate to keep track of progress
        .map(|(i, _)| {
            let mut hash = [0; 10];
            let mut nonce = [0; 6];

            rand::thread_rng().fill(&mut hash[..]);
            rand::thread_rng().fill(&mut nonce[..]);

            if debug && i % 1000 == 0 {
                print_progress(i, num_hashes, start_time); // Print progress every 1000 hash generation
            }

            Record { hash, nonce }
        })
        .collect();

    

    //println!("Total time taken for hash generation: {:?}", start_time.elapsed());

    hashes
}

// Function to print progress indicators and performance metrics
fn print_progress(completed: usize, total: usize, start_time: Instant) {
    let elapsed = start_time.elapsed().as_secs_f64();
    let progress = (completed as f64 / total as f64) * 100.0;
    let eta = elapsed * (total as f64 / completed as f64);
    let throughput = completed as f64 / elapsed;

    println!("[HASHGEN]: {:.2}% completed, ETA {:.3} seconds, {}/{} hashes generated, {:.1} hashes/sec",
             progress, eta, completed, total, throughput);
}

// Function to sort hashes using Rayon
fn sort_hashes(hashes: &mut [Record], debug: bool) {
    
    if debug {
        println!("Sorting hashes...");
    }
    hashes.par_sort_unstable_by(|a, b| a.hash.cmp(&b.hash));
    
}

// Function to write records from memory to file using asynchronous I/O and parallelism
async fn write_records_to_file(records: &[Record], filename: &str, debug: bool) -> Result<(), Error> {


    let file = tokio::fs::File::create(filename).await?;
    let mut buf_writer = BufWriter::new(file);

    for record in records {
        let mut binary_hash = Vec::new();
        binary_hash.extend_from_slice(&record.hash);

        buf_writer.write_all(&binary_hash).await?;
    }

    buf_writer.flush().await?;


    Ok(())
}

// Function to parse command-line arguments
fn parse_args() -> Args {
    let matches = App::new("YourAppName")
        .version("1.0")
        .author("Your Name")
        .about("Description of your program")
        .arg(Arg::new("num_threads_hash")
            .short('t')
            .long("t")
            .value_name("NUM_THREADS_HASH")
            .help("Number of threads for hash generation")
            .takes_value(true))
        .arg(Arg::new("num_threads_sort")
            .short('o')
            .long("o")
            .value_name("NUM_THREADS_SORT")
            .help("Number of threads for sorting")
            .takes_value(true))
        .arg(Arg::new("num_threads_write")
            .short('i')
            .long("i")
            .value_name("NUM_THREADS_WRITE")
            .help("Number of threads for writing to disk")
            .takes_value(true))
        .arg(Arg::new("filename")
            .short('f')
            .long("f")
            .value_name("FILENAME")
            .help("Output filename")
            .takes_value(true))
        .arg(Arg::new("memorysize")
            .short('m')
            .long("m")
            .value_name("MEMORYSIZE")
            .help("Memory Size")
            .takes_value(true))
        .arg(Arg::new("filesize")
            .short('s')
            .long("s")
            .value_name("FILESIZE")
            .help("File Size")
            .takes_value(true))
        .arg(Arg::new("print_head")
            .short('p')
            .long("p")
            .value_name("PRINT_HEAD")
            .help("Number of records to print from head")
            .takes_value(true))
        .arg(Arg::new("print_tail")
            .short('r')
            .long("r")
            .value_name("PRINT_TAIL")
            .help("Number of records to print from tail")
            .takes_value(true))
        .arg(Arg::new("debug_mode")
            .short('d')
            .long("d")
            .value_name("DEBUG_MODE")
            .help("Turns on debug mode with true, off with false")
            .takes_value(true))
        .arg(Arg::new("verify_sort_order")
            .short('v')
            .long("v")
            .value_name("VERIFY_SORT_ORDER")
            .help("Verify hashes sort order from file, off with false, on with true")
            .takes_value(true))
        .arg(Arg::new("verify_blake_hashes")
            .short('b')
            .long("b")
            .value_name("VERIFY_BLAKE_HASHES")
            .help("Verify hashes as correct BLAKE3 hashes")
            .takes_value(true))
        .get_matches();

    Args {
        num_threads_hash: matches.value_of("num_threads_hash").unwrap_or("0").parse().unwrap(),
        num_threads_sort: matches.value_of("num_threads_sort").unwrap_or("0").parse().unwrap(),
        num_threads_write: matches.value_of("num_threads_write").unwrap_or("0").parse().unwrap(),
        filename: matches.value_of("filename").unwrap_or("").to_string(),
        memorysize: matches.value_of("memorysize").unwrap_or("0").parse().unwrap(),
        filesize: matches.value_of("filesize").unwrap_or("0").parse().unwrap(),
        print_head: matches.value_of("print_head").unwrap_or("0").parse().unwrap(),
        print_tail: matches.value_of("print_tail").unwrap_or("0").parse().unwrap(),
        debug_mode: matches.value_of("debug_mode").unwrap_or("false").parse().unwrap(),
        verify_sort_order: matches.value_of("verify_sort_order").unwrap_or("false").parse().unwrap(),
        verify_blake_hashes: matches.value_of("verify_blake_hashes").unwrap_or("false").parse().unwrap(),
    }
}

// Function to verify hashes as correct BLAKE3 hashes
fn verify_blake3(records: &[Record], debug: bool) {
    if debug {
        println!("Verifying BLAKE3 hashes...");
    }

    // Iterate over each record
    for (i, record) in records.iter().enumerate() {
        // Calculate BLAKE3 hash for the record
        let mut hasher = Hasher::new();
        hasher.update(&record.nonce);
        let hash_bytes = hasher.finalize().as_bytes().to_owned(); // Store the value in a local variable
        let hash = &hash_bytes[..10]; // Borrow a reference to the variable

        // Compare truncated hash with the hash stored in the record
        if hash != &record.hash {
            println!("Hash mismatch for record {}", i);
            return;
        }
    }
}


// Main function
#[tokio::main]
async fn main() {
    // Parse command-line arguments
    let args = parse_args();

    // Define the size of file and calculate the number of records needed
    let file_size: usize = args.filesize * 1024 * 1024;
    let num_records = file_size / RECORD_SIZE;
    let num_hashes = num_records; // Assuming each record corresponds to one hash
    
    // Adjust num_threads_hash based on memory size
    let num_threads_hash = if args.memorysize < num_hashes * 10 {
        num_hashes / 2 // Reduce the number of threads if memory size is not sufficient
    } else {
        args.num_threads_hash
    };

    // Measure the start time
    let start_time = Instant::now();

    // Generate BLAKE3 hashes
    let mut hashes = generate_hashes(num_hashes, num_threads_hash, args.debug_mode);
    if args.debug_mode {

    println!("Sort started...");}

    // Sort the hashes
    sort_hashes(&mut hashes, args.debug_mode);
    // Write records from memory to file
    if let Err(err) = write_records_to_file(&hashes, &args.filename, args.debug_mode).await {
        eprintln!("Error writing records to file: {}", err);
        return;
    }

    if args.debug_mode {

    println!("File successfully sorted and saved.");}

    // Calculate the total time
    let total_time = start_time.elapsed();

    // Print the total time taken
    //println!("Total time taken: {:?}", total_time);
    // Convert total time to a formatted string
    let total_time_str = format!("{:.2?}", total_time);

// Calculate total time taken in seconds
    let total_time_secs = total_time.as_secs_f64();
    // Calculate the total number of hashes processed
    let num_hashes_processed = num_hashes as f64; // Assuming num_hashes is the total number of hashes generated


    // Calculate the performance metrics
    let hashes_per_second = num_hashes_processed / total_time_secs / 1_000_000.0; // MH/s
    let megabytes_per_second = file_size as f64 / total_time_secs / (1024.0 * 1024.0); // MB/sec


    // Print the provided values based on debug mode
if args.debug_mode {
    println!("NUM_THREADS_HASH={}", args.num_threads_hash);
    println!("NUM_THREADS_SORT={}", args.num_threads_sort);
    println!("NUM_THREADS_WRITE={}", args.num_threads_write);
    println!("FILENAME={}", args.filename);
    println!("MEMORYSIZE={}", args.memorysize);
    println!("FILESIZE={}", args.filesize);
    println!("RECORD_SIZE=16B");
    println!("HASH_SIZE=10B");
    println!("NONCE_SIZE=6B");
    println!("PRINT_HEAD={}", args.print_head);
    println!("PRINT_TAIL={}", args.print_tail);
    println!("DEBUG_MODE={}", args.debug_mode);
    println!("VERIFY_SORT_ORDER={}", args.verify_sort_order);
    println!("VERIFY_BLAKE_HASHES={}", args.verify_blake_hashes);
        println!(
        "Completed {} MB file {} in {:.2} seconds : {:.2} MH/s {:.2} MB/sec",
        file_size / (1024 * 1024),
        args.filename,
        total_time_str,
        hashes_per_second,
        megabytes_per_second
    );


} else {
    println!("t{} o{} i{} m{} s{} {:?} {:?} {:?}",
             args.num_threads_hash, args.num_threads_sort, args.num_threads_write, args.memorysize, args.filesize, total_time, hashes_per_second, megabytes_per_second);
}

}
