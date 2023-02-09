# buildpack-sniffer
Sniff out what buildpacks are in use (and how) on a given Cloud Foundry
deployment. This tool is intended to help understand how easy it will be to
migrate Cloud Foundry applications to v3 buildpacks.

## Usage

### Requirements

Currently, this script depends on the following (these may relax over time):
- Python 3.5+
- `cf` CLI targeting desired Cloud Foundry environment and logged in as an
  `admin` or `admin_read_only` user
- Cloud Foundry version that includes the v3 API

### Running

1. Clone this repo
1. `./main.py`

### Output

Output will be in `./output.json`

Data collected:
- Apps' guid
- Apps' state
- Apps' lifecycle type
- Apps' lifecycle buildpacks
- Apps' lifecycle stack
- Apps' current droplet's detected buildpack
- Apps' environment variable names (values are not collected)
- Apps' service bindings (name, label, and tags)

Example output:
```json
[
  {
    "guid": "8ab99c1c-ce0d-4184-b6d4-5d8a7076fd9a",
    "state": "STOPPED",
    "lifecycle": {
      "type": "buildpack",
      "buildpacks": [],
      "stack": "cflinuxfs3"
    },
    "current_droplet": {
      "buildpacks": [
        {
          "name": "ruby_buildpack",
          "detect_output": "ruby",
          "buildpack_name": "ruby",
          "version": "1.8.60"
        }
      ]
    },
    "env": {
      "vcap_services": [
        {
          "name": "my-service",
          "label": "a-service",
          "tags": [
            "servicing"
          ]
        }
      ],
      "staging_env_json": [],
      "running_env_json": [],
      "environment_variables": [
        "JAVA_OPTS"
      ]
    }
  }
]
```

## Running on Cloud Foundry

For a controlled environment with the required dependencies (python and cf
CLI), you can run the script on a Cloud Foundry component VM:

1. ssh onto a bosh instance with the cf CLI. A good way to get it is via the
   `cf-cli` bosh release. For example, in TAS, a `compute` or `clock_global`
   instance: `bosh ssh clock_global`.
1. `sudo su vcap`
1. Change into a directory owned by vcap (so we can retrieve the output file
   later). For example: `cd /var/vcap/data/cloud_controller_clock/tmp/`.
1. `wget https://raw.githubusercontent.com/Gerg/buildpack-sniffer/main/main.py`
1. `chmod +x main.py`
1. Get cf CLI on your path: `export PATH="$PATH:/var/vcap/packages/cf-cli-8-linux/bin"`
   (The exact path for the CLI may differ, depending on your deployment.)
1. `cf api <target api>`
1. Log in with admin_read_only credentials: `cf login`
1. `./main.py`
1. This will generate an `output.json` in the same directory
1. Exit the bosh instance
1. Bosh SCP the file off of the instance. For example: `bosh scp clock_global:/var/vcap/data/cloud_controller_clock/tmp/output.json /tmp/output.json`

## Development

For testing (or running, I suppose) on Python 3.5 via the included Dockerfile (requires Docker):

1. Navigate to the `buildpack-sniffer` directory
1. Get a Linux CF CLI in the directory. For example:
   ```
   $ wget https://packages.cloudfoundry.org/stable\?release\=linux64-binary\&version\=8.5.0\&source\=github-rel -O cf.tgz
   ...
   $ tar -xf cf.tgz
   ...
   $ mv cf8 cf
   ...
   ```
1. `docker build -t buildpack-sniffer .`
1. `docker run --env "CF_API=<cf API here>" --env "CF_USER=admin" --env "CF_PASSWORD=<admin password here>" buildpack-sniffer`

The Dockerfile is based on Ubuntu Xenial, which should be similar to the Xenial stemcell.
