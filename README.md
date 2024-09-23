# License Extractor

WorkTango has a need to see the license of every dependency our code repositories declare. This repo functions by taking an SBOM from GitHub and extracting all licenses from it, fetching any unknown licenses from the NPM registry or RubyGems registry, and exporting to CSV or JSON.

An SBOM is a Software Bill of Materials. It is all of the items your project depends on, with their dependencies listed as well. GitLab has published [a great article that gives an overview](https://about.gitlab.com/blog/2022/10/25/the-ultimate-guide-to-sboms/) of SBOM and its associated formats.

## Using this repo

This repo works on the SBOM JSON files, specifically those from GitHub. GitHub provides an SBOM through its Dependency Graph mapping feature. Example using the KW repo: https://github.com/KazooHR/kazoo-web/network/dependencies

This repo functions through a single Python script, `extract_licenses.py`. Why Python? Python is known for being extremely fast at working with files.

Each directory in the project represents a repo that WT owns. Each directory houses its own SBOM and generated JSON and  CSV files. All files are committed to source control. The files are kept to be able to see changes over time.

### Initializing dependencies
The latest version of python is used. It is recommended to use a python version manager, such as `pyenv`. The easiest way to acquire `pyenv` is to install it with homebrew:

```bash
brew install pyenv
```

pyenv can automatically switch to the correct version of python by reading `.python-version`. If it did not add it for you on installation, add the following to your shell rc file (i.e. `.zshrc`):

```zsh
export PYENV_ROOT="$HOME/.pyenv"
export PATH="$PYENV_ROOT/bin:$PATH"
eval "$(pyenv init --path)"
```

If necessary install, the required version of python in `.python-version`:
```bash
pyenv install 3.12.6
```

Next we need to install dependencies:
```bash
python -m venv venv
source myvenv/bin/activate
pip install -r requirements.txt
```

`venv` creates a virtual environment with the necessary dependencies from `requirements.txt`. This is analogous to establishing a package in node with a `package.json` file and installing the dependencies with `npm install`. Unlike npm python virtual environments need to be activated, placing us in an interactive environment. Lastly we install dependencies.

### Executing the script
With dependencies installed we are ready to go. Let's use the KW repo and it's dependencies for this example.

Download the latest version of the SBOM from GitHub: https://github.com/KazooHR/kazoo-web/network/dependencies

Rename the file to sbom.json and place it in `kw-licenses` (it is okay to overwrite the existing one, remember everything is version controlled!).

We are now ready to run the script. From the root of the repo:

```bash
python extract_licenses.py --base_path ./kw-licenses --output_format csv --filter_type unfiltered 
```

#### Arguments
Let's explore the arguments that be passed

- `--base_bath`: Which sub-directory containing the files you want to execute the script against
- `--output_format`: Takes options of `csv` or `json`.
- `--filter_type`: The script has the ability to filter out licenses that WT does not typically need to investigate or understand further (such as MIT or Apache 2.0). Possible options are `unfiltered` or `filtered`.

#### Output files
The primary output file will depend on if filtered or unfiltered results are chosen and then whether JSON or CSV are selected.

```bash
python extract_licenses.py --base_path ./kw-licenses --output_format csv --filter_type unfiltered 
```

This will produce:
`./kw-licenses/licenses-unfiltered.csv`

A cache file is generated or updated on each run of the script, `licenses-cache.json`. For some reason GitHub does not always capture a dependency's license. In this case we scrape the license from the NPM registry or RubyGem registry. This operation is subject to rate limiting, the cache file enables us to capture results if a single script execution fails.

It is recommended to delete the cache file each time you re-export the SBOM from GitHub. Sometimes licenses change and this ensures we capture the most recent information.

### Things of note and Troubleshooting
**Packages WT owns**
Any package that starts with `kazoo` is omitted as they are our own internal packages. These have no license and will result in failure looking them up (we own them so do not need them in the list even if they did have a license). Anything prepended with `action:` is also omitted as these are not real dependencies (they seem to potentially be localized dependencies?)

**Many of my results have LICENSE_FETCH_ERROR**
Likely this is the the result of rate limiting from the NPM registry or RubyGem registry. The script has a simple sleep command in-between fetches to avoid the limit, you can increase this limit for potentially more reliable fetching.

**My results contain LICENSE_NOT_FOUND/I'm seeing the output "License not found for package"**
Likely the registry updated their HTML. Scraping is more of an art than science. You may need to update the script with the proper HTML. You can utilize for Gemini/Vertex/GH Copilot for this if you are not familiar with Python! The script is simple enough that these AI tools can easily update it.

