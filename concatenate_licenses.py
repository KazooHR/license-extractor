import os
import csv
import argparse

def centralize_licenses(main_directory=".", output_file="combined_licenses.csv"):
    """
    Centralizes license data from multiple CSV files in subdirectories.

    Args:
        main_directory (str, optional): Path to the main directory containing subdirectories. Defaults to the current directory (".").
        output_file (str, optional): Name of the centralized CSV file to store all data. Defaults to "combined_licenses.csv".
    """

    unique_packages = {} 

    # Iterate through each subdirectory
    for subdir in os.listdir(main_directory):
        subdir_path = os.path.join(main_directory, subdir)
        if os.path.isdir(subdir_path):
            csv_file_path = os.path.join(subdir_path, "licenses-unfiltered.csv")
            print(f"Processing: {csv_file_path}")
            if os.path.exists(csv_file_path):
                with open(csv_file_path, 'r') as input_file:
                    reader = csv.reader(input_file)
                    next(reader)  # Skip header row

                    for row in reader:
                        package_name = row[0]
                        # Only add if the package name is not already in the dictionary
                        if package_name not in unique_packages: 
                            unique_packages[package_name] = row 

    # Write all unique rows to the output file
    with open(output_file, 'w', newline='') as output_file_handle: 
        writer = csv.writer(output_file_handle)
        writer.writerow(["Package Name", "License", "URL"])  # Write header
        writer.writerows(unique_packages.values())

    print(f"Centralized data has been written to {output_file}") 

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Centralize license data from CSV files in subdirectories.")
    parser.add_argument("-d", "--main_directory", default=".", help="Path to the main directory containing subdirectories. Defaults to the current directory.")
    parser.add_argument("-o", "--output_file", default="licenses_combined.csv", help="Name of the centralized CSV file to store all data. Defaults to 'licenses_combined.csv'.")
    args = parser.parse_args()

    centralize_licenses(args.main_directory, args.output_file)