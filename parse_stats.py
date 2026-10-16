#!/usr/bin/env python3
import argparse
import glob
import os
import re
import sys


def parse_arguments():
    parser = argparse.ArgumentParser(
        description="Extract metrics from gem5 report files and build a CSV matrix."
    )
    parser.add_argument(
        "--dir",
        default="rpts",
        help="Directory containing stat reports (default: rpts)",
    )
    parser.add_argument(
        "--search",
        default="simSeconds",
        help="Metric name to extract (default: simSeconds)",
    )
    parser.add_argument(
        "--output",
        default="results.csv",
        help="Output CSV file path (default: results.csv)",
    )
    return parser.parse_args()


def extract_metric_from_second_block(file_path, metric_name):
    """
    Extracts the specified metric strictly from the second simulation statistics block.
    """
    try:
        with open(file_path, "r", errors="ignore") as f:
            content = f.read()
    except Exception as e:
        print(f"Warning: Could not read {file_path}: {e}", file=sys.stderr)
        return None

    # Split the stats file by the simulation block markers
    blocks = content.split("---------- Begin Simulation Statistics ----------")

    # blocks[0] is pre-marker preamble
    # blocks[1] is 1st simulation block (bootup)
    # blocks[2] is 2nd simulation block (the actual benchmark run)
    if len(blocks) < 3:
        # Fallback if there is only 1 stats dump in the file
        if len(blocks) == 2:
            target_block = blocks[1]
        else:
            return None
    else:
        target_block = blocks[2]

    # Match metric name at start of line followed by whitespace and the float/int value
    pattern = rf"^{re.escape(metric_name)}\s+([0-9.eE+-]+)"
    match = re.search(pattern, target_block, re.MULTILINE)

    if match:
        return match.group(1)
    return None


def main():
    args = parse_arguments()

    # Find all files matching the pattern thread<T>_seed<S>.txt
    pattern = os.path.join(args.dir, "thread*_seed*.txt")
    files = glob.glob(pattern)

    if not files:
        print(f"Error: No matching report files found in '{args.dir}'.")
        sys.exit(1)

    # regex to parse thread and seed numbers from filename
    fname_regex = re.compile(r"thread(\d+)_seed(\d+)\.txt$")

    data = {}  # data[thread][seed] = value
    all_seeds = set()
    all_threads = set()

    for fpath in files:
        match = fname_regex.search(fpath)
        if not match:
            continue

        thread = int(match.group(1))
        seed = int(match.group(2))

        val = extract_metric_from_second_block(fpath, args.search)

        if thread not in data:
            data[thread] = {}
        data[thread][seed] = val if val is not None else "N/A"

        all_threads.add(thread)
        all_seeds.add(seed)

    sorted_threads = sorted(all_threads)
    sorted_seeds = sorted(all_seeds)

    # Write output CSV
    with open(args.output, "w") as out:
        # CSV Header: threads, 1, 2, ...
        header = ["threads"] + [str(s) for s in sorted_seeds]
        out.write(", ".join(header) + "\n")

        # Rows: thread_num, val1, val2, ...
        for t in sorted_threads:
            row = [str(t)]
            for s in sorted_seeds:
                row.append(str(data[t].get(s, "N/A")))
            out.write(", ".join(row) + "\n")

    print(f"Successfully parsed '{args.search}' across {len(files)} reports.")
    print(f"Results written to: {args.output}")


if __name__ == "__main__":
    main()


