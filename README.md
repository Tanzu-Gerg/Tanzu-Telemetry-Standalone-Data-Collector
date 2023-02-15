# Cloud Foundry Buildpack Data Collector
Collect data on what buildpacks are in use (and how) on a given Cloud Foundry
deployment. This tool is intended to help understand how easy it will be to
migrate Cloud Foundry applications to v3 buildpacks (aka [Cloud Native
Buildpacks](https://buildpacks.io/)).

## Usage

### Requirements

This script depends on the following:
- Python 3.5+
- `cf` CLI targeting desired Cloud Foundry deployment and logged in as an
  `admin` or `admin_read_only` user
- Cloud Foundry version that includes the v3 API

### Running

1. Clone this repo
1. `./main.py`

### Output

Output will be in `./output.json` in your current working directory.

Data collected for all apps:
- guid
- state
- lifecycle type (buildpack or docker)
- lifecycle buildpacks (user-requested buildpacks)
- lifecycle stack
- current droplet's detected buildpack
- environment variable names (in most cases, values are not collected)
- environment variable values for a small set of buildpack-related variables (see below)
- app service bindings (name, label, and tags)
- matching start command fragments from the web process (see below)

The start command fragments that will be collected are (nothing else from
process start commands are collected):
- `open_jdk_jre/bin/java `
- `springframework.boot.lader.JarLauncher`
- `groovy/bin/groovy `
- `spring_boot_cli/bin/spring run`
- `tomcat/bin/catalina.sh run`

The following fields will be anonymized by taking a sha256 hash of the values:
- app guids
- environment variables (excluding a small set of buildpack-related variables (see below))
- service binding names, labels, and tags

The un-anonymized environment variable names AND values that are collected are
as follows:
- `BP_PIP_VERSION` used by Python Buildpack
- `CACHE_NUGET_PACKAGES` used by .NET Core Buildpack
- `EXTENSIONS` used by PHP Buildpack
- `GOVERSION` used by Go Buildpack
- `JBP_CONFIG_COMPONENTS` used by Java Buildpack
- `JBP_CONFIG_SPRING_AUTO_RECONFIGURATION` used by Java Buildpack
- `JBP_DEFAULT_COMPONENTS` used by Java Buildpack
- `NODE_ENV` used by Node.js Buildpack
- `WEBDIR` used by PHP Buildpack
- `WEB_CONCURRENCY` used by Node.js Buildpack
- `WEB_MEMORY` used by Node.js Buildpack
- `WEB_SERVER` used by PHP Buildpack

Example output:
```json
[
  {
    "guid": "51a53d85d9546ef8bdd34d47d44b322e4f6a8b0488ccce6f1e7a8ce48d4e51e1",
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
          "tags": [
            "798f012674b5b8dcab4b00114bdf6738a69a4cdcf7ca0db1149260c9f81b73f7"
          ]
        },
        {
          "name": "be9b4c9674ae3932cf382b362458d6107e9433d1d9e05bef3eef187bb7785c05",
          "label": "6351e758fb69733d7d4ec5faea3cf7c2b1494db263eb0c0a2c889b2578114ec4",
          "tags": [
            "798f012674b5b8dcab4b00114bdf6738a69a4cdcf7ca0db1149260c9f81b73f7"
          ]
        }
      ],
      "staging_env": [
        "e919a75364398a449f860aeadddc57fa0502145a4e63959ddb33c417a48dc0da",
        "JBP_DEFAULT_COMPONENTS={jres: [\"JavaBuildpack::Jre::ZuluJRE\"]}",
        "a11b705f50010a321815b0a0aca534ab7aa89d597f32db9ffc7df459c8d61360",
        "JBP_CONFIG_COMPONENTS={jres: [\"JavaBuildpack::Jre::OpenJdkJRE\"]}",
        "JBP_CONFIG_SPRING_AUTO_RECONFIGURATION={enabled: false}"
      ],
      "running_env": [
        "c071cf5f5ed6f884cc70155b6f05f755fd46a302d05e4261b7e92ce878bbfed8",
        "JBP_DEFAULT_COMPONENTS={jres: [\"JavaBuildpack::Jre::ZuluJRE\"]}",
        "a11b705f50010a321815b0a0aca534ab7aa89d597f32db9ffc7df459c8d61360",
        "JBP_CONFIG_COMPONENTS={jres: [\"JavaBuildpack::Jre::OpenJdkJRE\"]}",
        "JBP_CONFIG_SPRING_AUTO_RECONFIGURATION={enabled: false}",
        "e919a75364398a449f860aeadddc57fa0502145a4e63959ddb33c417a48dc0da"
      ]
    },
    "process": {
      "command_fragments": [
        "tomcat/bin/catalina.sh run"
      ]
    }
  }
]
```

### Configuration

Environment variables (set in the shell executing the script):

|Var|Effect|
|-|-|
| `ANON_BP_VARS` | If set, anonymize buildpack-related environment variables. |
| `BYPASS_ANON` | If set, do not anonymize fields. |

Usage example:
```sh
BYPASS_ANON=1 ./main.py
```

## Running on Cloud Foundry

For a controlled environment with the required dependencies (python and cf
CLI), you can run the script on a Cloud Foundry component VM as follows:

1. ssh onto a bosh instance containing the cf CLI. A good way to get the CLI is
   via the [`cf-cli` bosh
   release](https://github.com/bosh-packages/cf-cli-release). For example, the
   `compute` or `clock_global` instance in
   [TAS](https://tanzu.vmware.com/application-service) (instance name depends
   on configuration): `bosh ssh clock_global`
1. Switch to the "vcap" user: `sudo su vcap`
1. Change into a directory owned by vcap (so we can retrieve the output file
   later). For example: `cd /var/vcap/data/cloud_controller_clock/tmp/`.
1. Download this script: `wget https://raw.githubusercontent.com/Gerg/buildpack-data-collector/main/main.py`
1. Make the script executable: `chmod +x main.py`
1. Add the cf CLI to your path: `export PATH="$PATH:/var/vcap/packages/cf-cli-8-linux/bin"`
   (The exact path for the CLI may differ, depending on your deployment.)
1. Target the desired Cloud Foundry API with the CLI: `cf api <target api>`
1. Log in with
   [admin_read_only](https://downey.io/notes/dev/create-cloud-foundry-read-only-admin/)
   or admin credentials: `cf login`
1. Execute the script: `./main.py`
1. The script will generate an `output.json` in your current directory
1. Exit the bosh instance
1. Bosh SCP the file off of the instance. For example:
   `bosh scp clock_global:/var/vcap/data/cloud_controller_clock/tmp/output.json /tmp/output.json`

As an additional benefit, running from within the bosh deployment also reduces
network latency, which can significantly speed up execution time.

## Performance

_This data was gathered prior to collecting process-level data and it out of
date. It will be updated to reflect new behavior shortly._

Performance for a trial against a deployment seeded with 10,000 apps (NOT app
instances), when run on a bosh instance (jammy stemcell), using the procedure
described above:
- Execution time: ~30 minutes
- Memory consumption: ~110M
- CPU consumption: ~1.4% of 2.20GHz CPU
- Output file size: ~7.3M

## Development

For testing (or running, I suppose) on Python 3.5 via the included Dockerfile (requires Docker):

1. Navigate to the `buildpack-data-collector` directory
1. Get a Linux CF CLI in the directory. For example:
   ```
   $ wget https://packages.cloudfoundry.org/stable\?release\=linux64-binary\&version\=8.5.0\&source\=github-rel -O cf.tgz
   ...
   $ tar -xf cf.tgz
   ...
   $ mv cf8 cf
   ...
   ```
1. `docker build -t buildpack-data-collector`
1. `docker run --env "CF_API=<cf API here>" --env "CF_USER=admin" --env "CF_PASSWORD=<admin password here>" buildpack-data-collector`

The Dockerfile is based on Ubuntu Xenial, which should be similar to the Xenial stemcell.
