import json
import csv
import argparse
import requests
from bs4 import BeautifulSoup
import time
import os

LICENSE_NOT_FOUND = "LICENSE NOT FOUND"
LICENSE_FETCH_ERROR = "LICENSE FETCH ERROR"

def fetch_license_from_npm(package_name):
    """Fetches license information from the NPM registry."""

    npm_url = f"https://npmjs.com/{package_name}"
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
                return license_text.text.strip()

        print(f"License not found for package: {package_name} (URL: {npm_url})")
        return LICENSE_NOT_FOUND

    else:
        print(response)
        print(f"Error fetching license for package: {package_name} (URL: {npm_url})")
        return LICENSE_FETCH_ERROR

def fetch_license_from_rubygems(package_name):
    """Fetches license information from the RubyGems registry."""

    # Strip out "rubygems:" prefix if present
    package_name = package_name.replace("rubygems:", "")

    rubygems_url = f"https://rubygems.org/gems/{package_name}"
    response = requests.get(rubygems_url)

    if response.status_code == 200:
        soup = BeautifulSoup(response.text, 'html.parser')

        # Find the <span> with class 'gem__ruby-version'
        license_header = soup.find('span', class_='gem__ruby-version') 

        if license_header:
            # Find the child <p> tag within the <span>
            license_text = license_header.find('p')
            if license_text:
                return license_text.text.strip()

        print(f"License not found for package: {package_name} (URL: {rubygems_url})")
        return LICENSE_NOT_FOUND

    else:
        print(response)
        print(f"Error fetching license for package: {package_name} (URL: {rubygems_url})")
        return LICENSE_FETCH_ERROR


def extract_licenses(output_format, base_path, filter_type="filtered", registry="npm"):
    """Extracts license information from sbom.json and creates a file in the specified format."""

    sbom_path = os.path.join(base_path, "sbom.json")
    licenses_cache_path = os.path.join(base_path, "licenses-cache.json")

    with open(sbom_path, "r") as sbom_file:
        sbom_data = json.load(sbom_file)

    # Load all licenses if they exist
    if os.path.exists(licenses_cache_path):
        with open(licenses_cache_path, "r") as unfiltered_file:
            package_licenses = json.load(unfiltered_file)
    else:
        package_licenses = {}

    # Set the output file based on the user supplied argument
    if output_format == "json":
        output_file = os.path.join(base_path, f"licenses-{filter_type}.json")  # Construct path
    elif output_format == "csv":
        output_file = os.path.join(base_path, f"licenses-{filter_type}.csv")  # Construct path
    else:
        print("Invalid output format. Please specify either 'json' or 'csv'.")
        return

    filtered_licenses = []
    for package in sbom_data["packages"]:
        # Skip packages we own or are part of the monorepo
        # The kazooohr with triple "o" is not a typo
        if "kazooohr" not in package["name"].lower() and "kazoohr" not in package["name"].lower() and "worktango" not in package["name"].lower() and not package["name"].startswith("actions:"):
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
                if registry == "npm":
                    license_concluded = fetch_license_from_npm(package_name_without_npm)
                elif registry == "rubygem":
                    license_concluded = fetch_license_from_rubygems(package_name_without_npm)
                else:
                    print(f"Unsupported registry: {registry}")
                    return

                # Throttle requests (adjust the delay as needed)
                time.sleep(3)

            package_licenses[package["name"]] = license_concluded

            # Create a dictionary for each package
            package_info = {
                "Package Name": package_name_without_npm, 
                "License": license_concluded,
                "URL": f"https://npmjs.com/package/{package_name_without_npm}" if registry == "npm" else f"https://rubygems.org/gems/{package_name_without_npm}"
            }

            # Filter for licenses NOT containing "MIT" or "Apache-2.0" if filter_type is "filtered"
            if filter_type == "unfiltered" or ("MIT" not in license_concluded and "Apache-2.0" not in license_concluded):
                filtered_licenses.append(package_info)

    # Always write to unfiltered-licenses.json
    with open(licenses_cache_path, "w") as unfiltered_file:
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
    parser.add_argument("--output_format", choices=["json", "csv"], required=True, help="Output format (json or csv)")
    parser.add_argument("--base_path", default=os.getcwd(), help="Path to the directory containing sbom.json and other files. Defaults to current directory.")
    parser.add_argument("--filter_type", choices=["filtered", "unfiltered"], default="filtered", help="Filter licenses (filtered or unfiltered). Defaults to filtered.")
    parser.add_argument("--registry", choices=["npm", "rubygem"], default="npm", help="Package registry to use for fetching license information. Defaults to npm.") 
    args = parser.parse_args()

    extract_licenses(args.output_format, args.base_path, args.filter_type, args.registry)