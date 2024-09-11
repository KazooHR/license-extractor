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

    # This operates as a cache to store all gathered licenses
    # for packages. There are two reasons for this:
    # 1. To avoid fetching the same license multiple times for the same package from the NPM registry.
    # 2. The primary output files have certain licenses filtered out but we still want a reference to all licenses.
    kw_unfiltered_licenses_file = "kw-unfiltered-licenses.json"
    
    # Load all licenses if they exist
    if os.path.exists(kw_unfiltered_licenses_file):
        with open(kw_unfiltered_licenses_file, "r") as unfiltered_file:
            package_licenses = json.load(unfiltered_file)
    # Otherwise, create an empty dictionary
    else:
        package_licenses = {}

    # Set the output file based on the user supplied argument
    if output_format == "json":
        output_file = "kw-licenses.json"
    elif output_format == "csv":
        output_file = "kw-licenses.csv"
    else:
        print("Invalid output format. Please specify either 'json' or 'csv'.")
        return

    filtered_licenses = {}
    for package in sbom_data["packages"]:
        # Skip packages we own or are part of the monorepo
        if package["name"] != "com.github.KazooHR/kazoo-web" and "@kazoohr/" not in package["name"] and not package["name"].startswith("actions:"):
            # Only fetch licenses for packages we haven't already fetched
            if package["name"] not in package_licenses:
                license_concluded = package.get("licenseConcluded", None)  # Get licenseConcluded, or None if missing

                if license_concluded is None:
                    # Fetch license information from NPM registry
                    npm_url = f"https://npmjs.com/{package['name'].replace('npm:', '')}"  # Remove "npm:" prefix if present
                    response = requests.get(npm_url)

                    if response.status_code == 200:
                        soup = BeautifulSoup(response.text, 'html.parser')
                        # Scraping shenanigans to find the license
                        # Huzzah!
                        
                        # Find all <h3> License tags on the page
                        license_headers = soup.find_all('h3', text='License')

                        # Loop through each license header
                        for license_header in license_headers:
                            # Check for a sibling <p> containing license text
                            license_text = license_header.find_next_sibling('p')
                            if license_text:
                                license_concluded = license_text.text.strip()
                                break

                        if license_concluded is None:  
                            license_concluded = "LICENSE NOT FOUND"
                            print(f"License not found for package: {package['name']} (URL: {npm_url})")

                    else:
                        # It is useful to know if we failed to fetch the license
                        # Likely this means the HTML scraping code needs to be updated
                        license_concluded = "LICENSE FETCH ERROR"
                        print(f"Error fetching license for package: {package['name']} (URL: {npm_url})")  # Print the URL

                package_licenses[package["name"]] = license_concluded

                # Filter for licenses NOT containing "MIT" or "Apache 2.0"
                if "MIT" not in license_concluded and "Apache 2.0" not in license_concluded:
                    filtered_licenses[package["name"]] = license_concluded

                # Throttle requests (adjust the delay as needed)
                time.sleep(3)  # Wait for 1 second

    # Always write to kw-unfiltered-licenses.json
    with open(kw_unfiltered_licenses_file, "w") as unfiltered_file:
        json.dump(package_licenses, unfiltered_file, indent=4)

    # Write filtered licenses to the specified format
    if output_format == "json":
        with open(output_file, "w") as licenses_file:
            json.dump(filtered_licenses, licenses_file, indent=4)
    elif output_format == "csv":
        with open(output_file, "w", newline="") as licenses_file:
            csv_writer = csv.DictWriter(licenses_file, fieldnames=["Package Name", "License"])
            csv_writer.writeheader()
            for package_name, license_concluded in filtered_licenses.items():
                csv_writer.writerow({"Package Name": package_name, "License": license_concluded})
    else:
        print("Invalid output format. Please specify either 'json' or 'csv'.")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Extract license information from SBOM.")
    parser.add_argument("output_format", choices=["json", "csv"], help="Output format (json or csv)")
    args = parser.parse_args()

    extract_licenses(args.output_format)