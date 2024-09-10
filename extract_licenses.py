import json
import csv
import argparse

def extract_licenses(output_format):
    """Extracts license information from kazoo-web-sbom.json and creates a file in the specified format."""

    with open("kazoo-web-sbom.json", "r") as sbom_file:
        sbom_data = json.load(sbom_file)

    package_licenses = {}

    for package in sbom_data["packages"]:
        if package["name"] != "com.github.KazooHR/kazoo-web" and "@kazoohr/" not in package["name"]:  # Skip main project and packages containing "@kazoohr/"
            license_concluded = package.get("licenseConcluded", "LICENSE NOT DETECTED")
            package_licenses[package["name"]] = license_concluded

    if output_format == "json":
        with open("kw-licenses.json", "w") as licenses_file:
            json.dump(package_licenses, licenses_file, indent=4)
    elif output_format == "csv":
        with open("kw-licenses.csv", "w", newline="") as licenses_file:
            csv_writer = csv.writer(licenses_file)
            csv_writer.writerow(["Package Name", "License"])  # Write header row with renamed column
            for package_name, license_concluded in package_licenses.items():
                csv_writer.writerow([package_name, license_concluded])
    else:
        print("Invalid output format. Please specify either 'json' or 'csv'.")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Extract license information from SBOM.")
    parser.add_argument("output_format", choices=["json", "csv"], help="Output format (json or csv)")
    args = parser.parse_args()

    extract_licenses(args.output_format)