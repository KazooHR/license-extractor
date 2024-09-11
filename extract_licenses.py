import json
import csv
import argparse
import requests
from bs4 import BeautifulSoup
import time
import os

def extract_licenses(output_format):
    """Extracts license information from kazoo-web-sbom.json and creates a file in the specified format."""

    with open("kazoo-web-sbom.json", "r") as sbom_file:
        sbom_data = json.load(sbom_file)

    package_licenses = {}

    if output_format == "json":
        output_file = "kw-licenses.json"
    elif output_format == "csv":
        output_file = "kw-licenses.csv"
    else:
        print("Invalid output format. Please specify either 'json' or 'csv'.")
        return

    if os.path.exists(output_file):
        if output_format == "json":
            with open(output_file, "r") as existing_file:
                package_licenses = json.load(existing_file)
        elif output_format == "csv":
            with open(output_file, "r") as existing_file:
                reader = csv.DictReader(existing_file)
                package_licenses = {row["Package Name"]: row["License"] for row in reader}

    for package in sbom_data["packages"]:
        if package["name"] != "com.github.KazooHR/kazoo-web" and "@kazoohr/" not in package["name"] and not package["name"].startswith("actions:"):
            if package["name"] not in package_licenses:
                license_concluded = package.get("licenseConcluded", None)  # Get licenseConcluded, or None if missing

                if license_concluded is None:
                    # Fetch license information from NPM registry
                    npm_url = f"https://npmjs.com/{package['name'].replace('npm:', '')}"  # Remove "npm:" prefix if present
                    response = requests.get(npm_url)

                    if response.status_code == 200:
                        soup = BeautifulSoup(response.text, 'html.parser')

                        # Find all <h3> License tags on the page
                        license_headers = soup.find_all('h3', text='License')

                        # Loop through each license header
                        for license_header in license_headers:
                            # Check for a sibling <p> containing license text
                            license_text = license_header.find_next_sibling('p')
                            if license_text:
                                license_concluded = license_text.text.strip()
                                break  # Stop looping after finding the license

                        if license_concluded is None:  # If no valid license is found
                            license_concluded = "LICENSE NOT FOUND"
                            print(f"License not found for package: {package['name']} (URL: {npm_url})")

                    else:
                        license_concluded = "LICENSE FETCH ERROR"
                        print(f"Error fetching license for package: {package['name']} (URL: {npm_url})")  # Print the URL

                package_licenses[package["name"]] = license_concluded

                # Throttle requests (adjust the delay as needed)
                time.sleep(1)  # Wait for 1 second

    if output_format == "json":
        with open("kw-licenses.json", "w") as licenses_file:
            json.dump(package_licenses, licenses_file, indent=4)
    elif output_format == "csv":
        with open("kw-licenses.csv", "w", newline="") as licenses_file:
            csv_writer = csv.DictWriter(licenses_file, fieldnames=["Package Name", "License"])
            csv_writer.writeheader()
            for package_name, license_concluded in package_licenses.items():
                csv_writer.writerow({"Package Name": package_name, "License": license_concluded})
    else:
        print("Invalid output format. Please specify either 'json' or 'csv'.")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Extract license information from SBOM.")
    parser.add_argument("output_format", choices=["json", "csv"], help="Output format (json or csv)")
    args = parser.parse_args()

    extract_licenses(args.output_format)