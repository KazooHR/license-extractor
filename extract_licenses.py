import json
import csv
import argparse
import requests
from bs4 import BeautifulSoup
import time
import os

LICENSE_NOT_FOUND = "LICENSE NOT FOUND"
LICENSE_FETCH_ERROR = "LICENSE FETCH ERROR"

def extract_licenses(output_format, base_path, filter_type="filtered"):
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
        if "kazooohr" not in package["name"].lower() and "kazoohr" not in package["name"].lower() and "worktango" not in package["name"].lower() and not package["name"].startswith("actions:"):
            license_concluded = None

            # Check if license is already in the package
            if "licenseConcluded" in package:
                license_concluded = package["licenseConcluded"]
                
            # Check if license is in the cache and it's not already marked as "LICENSE NOT FOUND" or "LICENSE FETCH ERROR"
            elif package["name"] in package_licenses and package_licenses[package["name"]] not in [LICENSE_NOT_FOUND, LICENSE_FETCH_ERROR]:
                license_concluded = package_licenses[package["name"]]
            
            # If license is not in either, or is marked as "LICENSE NOT FOUND" or "LICENSE FETCH ERROR", fetch it
            else:
                """
                Package names are prefixed with npm:, rubygems:, github:, etc.
                We need need the actual package name without prefix
                """
                package_name_without_prefix = package["name"].split(":", 1)[1]
                print(f"Fetching license for package: {package_name_without_prefix}")
                if package["name"].startswith("npm:"):
                    license_concluded = fetch_license_from_npm(package_name_without_prefix)
                elif package["name"].startswith("rubygems:"):
                    license_concluded = fetch_license_from_rubygems(package_name_without_prefix)
                elif package["name"].startswith("swift:"):
                    license_concluded = fetch_license_from_github(package_name_without_prefix)
                elif package["name"].startswith("go:"):
                    license_concluded = fetch_license_for_go_package(package_name_without_prefix)
                else:
                    print(f"Unsupported package prefix: {package['name']}")
                    continue  # Skip this package if the prefix is not recognized

                # Throttle requests (adjust the delay as needed)
                time.sleep(3)

            package_licenses[package["name"]] = license_concluded

            # Create a dictionary for each package
            package_info = build_package_info(package, license_concluded)

            # Filter for licenses NOT containing MIT or Apache 2 licenses if filter_type is "filtered"
            apache_licenses = ("MIT", "Apache-2.0", "Apache 2.0", "Apache 2")
            if filter_type == "unfiltered" or not any(license in license_concluded for license in apache_licenses):
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

def fetch_license_for_go_package(package_name):
    print(f"Fetching license for Go package: {package_name}")
    if package_name.startswith("github.com"):
        return fetch_license_from_github(package_name)
    else:
        # Go repositories all seem to use the same documentation service
        # which doesn't have a license field and doesn't seem to have a standard way to get the license
        error_message = "CANNOT AUTOMATICALLY FETCH LICENSE FOR NON-GITHUB GO PACKAGES"
        print(f"{package_name}: {error_message}")
        return error_message


def fetch_license_from_github(package_name):
    """
    Fetches license information from GitHub.
    """

    github_package = f"https://{package_name}"
    response = requests.get(github_package)

    if response.status_code == 200:
        soup = BeautifulSoup(response.text, 'html.parser')

        """
        Find the HTML that contians the text 'license'
        At the time of this writing would be in this format:
         <span data-component="text" data-content="MIT license">MIT license</span>
        """
        license_span = soup.find('span', attrs={'data-content': lambda x: x and 'license' in x})
        if license_span:
            return license_span.text.strip()

        print(f"License not found for package: {package_name} (URL: {github_package})")
        return LICENSE_NOT_FOUND

    else:
        print(response)
        print(f"Error fetching license for package: {package_name} (URL: {github_package})")
        return LICENSE_FETCH_ERROR

def build_package_info(package, license_concluded):
    """
    Builds a dictionary containing package information, including the URL based on the package prefix.

    Args:
        package: A dictionary containing package details, including the "name" key.
        package_name_without_prefix: The package name without any prefix.
        license_concluded: The concluded license for the package.

    Returns:
        A dictionary containing package information, including "Package Name", "License", and "URL".
    """

    package_name_without_prefix = package["name"].split(":", 1)[1] 
    package_info = {
        "Package Name": package_name_without_prefix, 
        "License": license_concluded
    }

    url_formats = {
        "npm:": "https://npmjs.com/package/{package_name}",
        "rubygems:": "https://rubygems.org/gems/{package_name}",
        "pip": "https://pypi.org/project/{package_name}",
        # Swift packages are GitHub URLs
        "swift": "{package_name}",
        # Go packages are URLs
        "go:": "{package_name}"
    }

    for prefix, url_format in url_formats.items():
        if package["name"].startswith(prefix):
            package_info["URL"] = url_format.format(package_name=package_name_without_prefix)
            break

    if "URL" not in package_info:
        raise ValueError(f"No matching URL format found for package prefix in '{package['name']}'. Does the URL format need to be added to the 'url_formats' dictionary?")

    return package_info


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Extract license information from SBOM.")
    parser.add_argument("--output_format", default="csv", choices=["json", "csv"], help="Output format (json or csv)")
    parser.add_argument("--base_path", required=True, help="Path to the directory containing sbom.json and other files. Defaults to current directory.")
    parser.add_argument("--filter_type", choices=["filtered", "unfiltered"], default="filtered", help="Filter licenses (filtered or unfiltered). Defaults to filtered.")
    args = parser.parse_args()

    extract_licenses(args.output_format, args.base_path, args.filter_type)