import json
import csv
import argparse
import requests
from bs4 import BeautifulSoup
import time
import os

LICENSE_NOT_FOUND = "LICENSE NOT FOUND"
LICENSE_FETCH_ERROR = "LICENSE FETCH ERROR"

def extract_licenses(output_format, base_path):
    """Extracts license information from sbom.json and creates a file in the specified format."""

    sbom_path = os.path.join(base_path, "sbom.json")  # Construct path to sbom.json
    unfiltered_licenses_path = os.path.join(base_path, "unfiltered-licenses.json")

    with open(sbom_path, "r") as sbom_file:
        sbom_data = json.load(sbom_file)

    # Load all licenses if they exist
    if os.path.exists(unfiltered_licenses_path):
        with open(unfiltered_licenses_path, "r") as unfiltered_file:
            package_licenses = json.load(unfiltered_file)
    else:
        package_licenses = {}

    # Set the output file based on the user supplied argument
    if output_format == "json":
        output_file = os.path.join(base_path, "filtered-licenses.json")  # Construct path
    elif output_format == "csv":
        output_file = os.path.join(base_path, "filtered-licenses.csv")  # Construct path
    else:
        print("Invalid output format. Please specify either 'json' or 'csv'.")
        return

    filtered_licenses = []
    for package in sbom_data["packages"]:
        # Skip packages we own or are part of the monorepo
        # The kazooohr with triple "o" is not a typo
        if package["name"] != "com.github.KazooHR/kazoo-web" and "@kazooohr/" not in package["name"] and "@kazoohr/" not in package["name"] and not package["name"].startswith("actions:"):
            package_name_without_npm = package["name"].replace("npm:", "") 
            license_concluded = None
            # Check if license is already in the package
            if "licenseConcluded" in package:
                license_concluded = package["licenseConcluded"]
                
            # Check if license is in the cache and it's not already marked as "LICENSE NOT FOUND" or "LICENSE FETCH ERROR"
            elif package["name"] in package_licenses and package_licenses[package["name"]] not in [LICENSE_NOT_FOUND, LICENSE_FETCH_ERROR]:
                license_concluded = package_licenses[package["name"]]
            
            # If license is not in either, or is marked as "LICENSE NOT FOUND" or "LICENSE FETCH ERROR", fetch it
            else:
                # Fetch license information from NPM registry
                npm_url = f"https://npmjs.com/{package_name_without_npm}"  # Remove "npm:" prefix if present
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
                            break

                    if license_concluded is None:  
                        license_concluded = LICENSE_NOT_FOUND
                        print(f"License not found for package: {package['name']} (URL: {npm_url})")

                else:
                    # It is useful to know if we failed to fetch the license
                    # Likely this means the HTML scraping code needs to be updated
                    print(response)
                    license_concluded = LICENSE_FETCH_ERROR
                    print(f"Error fetching license for package: {package['name']} (URL: {npm_url})")  # Print the URL

                # Throttle requests (adjust the delay as needed)
                time.sleep(3)  # Wait for 1 second

            package_licenses[package["name"]] = license_concluded

            # Filter for licenses NOT containing "MIT" or "Apache-2.0"
            if "MIT" not in license_concluded and "Apache-2.0" not in license_concluded:
                # Create a dictionary for each package
                package_info = {
                    "Package Name": package_name_without_npm, 
                    "License": license_concluded,
                    "URL": f"https://npmjs.com/package/{package_name_without_npm}" 
                }
                filtered_licenses.append(package_info)

    # Always write to unfiltered-licenses.json
    with open(unfiltered_licenses_path, "w") as unfiltered_file:
        json.dump(package_licenses, unfiltered_file, indent=4)

    # Write filtered licenses to the specified format
    if output_format == "json":
        with open(output_file, "w") as licenses_file:
            json.dump(filtered_licenses, licenses_file, indent=4)  # Dump the list of dictionaries
    elif output_format == "csv":
        with open(output_file, "w", newline="") as licenses_file:
            csv_writer = csv.DictWriter(licenses_file, fieldnames=["Package Name", "License", "URL"])  # Add URL field
            csv_writer.writeheader()
            for package_info in filtered_licenses:
                csv_writer.writerow(package_info)
    else:
        print("Invalid output format. Please specify either 'json' or 'csv'.")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Extract license information from SBOM.")
    parser.add_argument("output_format", choices=["json", "csv"], help="Output format (json or csv)")
    parser.add_argument("base_path", default=os.getcwd(), nargs='?', help="Path to the directory containing sbom.json and other files. Defaults to current directory.")
    args = parser.parse_args()

    extract_licenses(args.output_format, args.base_path)