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

The following fields will be anonymized by taking a sha256 hash of the values:
- Environment variable names

Example output:
```json
[
  {
    "guid": "9ffd6678-a74b-4ebe-8137-5617dd87b941",
    "state": "STARTED",
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
          "version": "1.9.1"
        }
      ]
    },
    "env": {
      "vcap_services": [
        {
          "name": "c3ab8ff13720e8ad9047dd39466b3c8974e592c2fa383d4a3960714caef0c4f2",
          "label": "6351e758fb69733d7d4ec5faea3cf7c2b1494db263eb0c0a2c889b2578114ec4",
          "tags": ["798f012674b5b8dcab4b00114bdf6738a69a4cdcf7ca0db1149260c9f81b73f7"]
        }
      ],
      "staging_env_json": [
        "e919a75364398a449f860aeadddc57fa0502145a4e63959ddb33c417a48dc0da"
      ],
      "running_env_json": [
        "c071cf5f5ed6f884cc70155b6f05f755fd46a302d05e4261b7e92ce878bbfed8"
      ],
      "environment_variables": [
        "2c26b46b68ffc68ff99b453c1d30413413422d706483bfa0f98a5e886266e7ae"
      ]
    }
  }
]
```

### Configuration

Environment variables:

|Var|Effect|
|-|-|
| `BYPASS_ANON` | If set, do not anonymize fields. |

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
