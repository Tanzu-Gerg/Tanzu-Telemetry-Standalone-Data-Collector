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

Data collected for all apps:
- guid
- state
- lifecycle type
- lifecycle buildpacks
- lifecycle stack
- current droplet's detected buildpack
- Environment variable names (in most cases, values are not collected)
- Environment variable values for a small set of Java Buildpack-related variables (see below)
- App service bindings (name, label, and tags)

The following fields will be anonymized by taking a sha256 hash of the values:
- Environment variable names (excluding a small set of Java Buildpack-related variables (see below))
- Service binding names, labels, and tags

The un-anonymized environment variables and values that are collected are as follows:
- `JBP_DEFAULT_COMPONENTS`
- `JBP_CONFIG_COMPONENTS`
- `JBP_CONFIG_SPRING_AUTO_RECONFIGURATION`

Example output:
```json
[
  {
    "guid": "69088a94-fe86-4a8c-9695-c4861d020dce",
    "state": "STARTED",
    "lifecycle": {
      "type": "buildpack",
      "buildpacks": [],
      "stack": "cflinuxfs3"
    },
    "current_droplet": {
      "buildpacks": [
        {
          "name": "java_buildpack",
          "detect_output": "java",
          "buildpack_name": "java",
          "version": "v4.53-https://github.com/cloudfoundry/java-buildpack#526dbcce"
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
      "staging_env": [
        "e919a75364398a449f860aeadddc57fa0502145a4e63959ddb33c417a48dc0da",
        "JBP_DEFAULT_COMPONENTS={jres: [\"JavaBuildpack::Jre::ZuluJRE\"]}"
      ],
      "running_env": [
        "c071cf5f5ed6f884cc70155b6f05f755fd46a302d05e4261b7e92ce878bbfed8",
        "JBP_DEFAULT_COMPONENTS={jres: [\"JavaBuildpack::Jre::ZuluJRE\"]}"
      ],
      "environment_variables": [
        "a11b705f50010a321815b0a0aca534ab7aa89d597f32db9ffc7df459c8d61360",
        "JBP_CONFIG_COMPONENTS={jres: [\"JavaBuildpack::Jre::OpenJdkJRE\"]}",
        "JBP_CONFIG_SPRING_AUTO_RECONFIGURATION={enabled: false}"
      ]
    }
  }
]
```

### Configuration

Environment variables:

|Var|Effect|
|-|-|
| `ANON_JBP` | If set, anonymize Java Buildpack-related environment variables. |
| `BYPASS_ANON` | If set, do not anonymize fields. |

Usage example:
```sh
BYPASS_ANON=1 ./main.py
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

Running from within the bosh deployment also reduces network latency, which can
speed up execution time.

## Performance

Performance for a trial against an environment seeded with 10,000 apps (NOT app
instances), when run on a bosh instance (jammy stemcell), as described above:
- Execution time: ~30 minutes
- Memory consumption: ~110M
- CPU consumption: ~1.4% of 2.20GHz CPU
- Output file size: ~7.3M

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
