import os
import csv
import argparse
import extract_licenses;

def centralize_licenses(main_directory, filtered, output_file, extract_missing_files):
    """
    Centralizes license data from multiple CSV files in subdirectories.

    Args:
        main_directory (str, optional): Path to the main directory containing subdirectories. Defaults to the current directory (".").
        filtered (bool, optional): Whether to combine filtered or unfiltered license files. Defaults to True (filtered).
        output_file (str, optional): Name of the centralized CSV file to store all data. Defaults to "combined_licenses.csv".
    """

    unique_packages = {}

    input_filename = "licenses-filtered.csv" if filtered else "licenses-unfiltered.csv" 
    output_filename = f"{output_file}-filtered.csv" if filtered else f"{output_file}-unfiltered.csv"
    print(f"Combining {"filtered" if filtered else "unfiltered"} files")

    print_instructions_for_skipped_files = False
    # Iterate through each subdirectory
    for subdir in os.listdir(main_directory):
        subdir_path = os.path.join(main_directory, subdir)
        if os.path.isdir(subdir_path):
            csv_file_path = os.path.join(subdir_path, input_filename)
            print(f"Processing: {csv_file_path}")
            csv_exists = os.path.exists(csv_file_path)
            if csv_exists or extract_missing_files:
                if not csv_exists and extract_missing_files:
                    print(f"CSV not found, extracting licenses: {csv_file_path}")
                    extract_licenses.extract_licenses("csv", subdir_path, "unfiltered" if not filtered else "filtered")
                with open(csv_file_path, 'r') as input_file_handle:
                    reader = csv.reader(input_file_handle)
                    next(reader)  # Skip header row

                    for row in reader:
                        package_name = row[0]
                        if package_name not in unique_packages:
                            unique_packages[package_name] = row
            else:
                print_instructions_for_skipped_files = True
                print(f"No CSV found, skipping: {csv_file_path}")

    if print_instructions_for_skipped_files:
        print("Some subdirectories did not have CSV files. Make sure to run extract_licenses.py first for each subdirectory.")
    # Write all unique rows to the output file
    with open(output_filename, 'w', newline='') as output_file_handle:
        writer = csv.writer(output_file_handle)
        writer.writerow(["Package Name", "License", "URL"])  # Write header
        writer.writerows(unique_packages.values())

    print(f"Combined license data has been written to {output_filename}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Centralize license data from CSV files in subdirectories.")
    parser.add_argument("-d", "--main_directory", default="./repo-sboms/", help="Path to the main directory containing subdirectories. Defaults to the current directory.")
    parser.add_argument("-u", "--unfiltered", default=False, action='store_false', help="Combine unfiltered License files from subdirectories.")
    parser.add_argument("-o", "--output_file", default="licenses-combined", help="Name of the centralized CSV file to store all data. Defaults to 'licenses_combined.csv'.")
    parser.add_argument("-e", "--extract_missing_files", default=True, action="store_true", help="Extract missing files from subdirectories.")
    args = parser.parse_args()

    filtered = not args.unfiltered 

    centralize_licenses(args.main_directory, filtered, args.output_file, args.extract_missing_files)