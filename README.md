# Tanzu Telemetry Standalone Data Collector and Submitter
Collect data on what buildpacks are in use (and how) on a given TAS
foundation. This tool is intended to help understand how easy it will be to
migrate TAS applications to v3 buildpacks (aka [Cloud Native
Buildpacks](https://buildpacks.io/)).

## Usage

At a high level, usage steps are as follows:
1. Run the collector script to gather data from a TAS foundation
1. (Optional) Review collected data
1. Run the submitter executable to send collected data to the TAS telemetry
   system

### Requirements

This script depends on the following:
- Python 3.5+
- `cf` CLI
- `admin` or `admin_read_only` user or client

### (Optional) Running on a TAS VM

For a controlled environment with the required dependencies (python and cf
CLI), you can run the script on a TAS component VM. As an additional benefit,
running from within the bosh deployment also reduces network latency, which can
significantly speed up execution time.

1. ssh onto an instance containing the cf CLI. For example, the
   `control` or `clock_global` instance in TAS (instance name depends
   on configuration): `bosh ssh clock_global/0`
1. Switch to the "vcap" user: `sudo su vcap`
1. Switch to a directory the "vcap" user has write access to. For example: `cd $HOME`
1. Add the cf CLI to your path: `export PATH="$PATH:/var/vcap/packages/cf-cli-8-linux/bin"`
1. Follow the "Collecting Data" and "Submitting Data" steps below

#### Copying Output File from Bosh Instance

Follow these steps if you would like to transfer the output file from the bosh
instance for analysis. These steps are for your convenience, and are not
required if you are submitting the output data directly from the bosh instance.

1. Copy the output file into a bosh-readable directory. For example:
   `cp output.json /var/vcap/data/cloud_controller_clock/tmp/`.
1. Bosh SCP the file off of the instance. For example:
   `bosh scp clock_global/0:/var/vcap/data/cloud_controller_clock/tmp/output.json /tmp/output.json`

### Collecting Data

1. Target the desired TAS foundation: `cf api <target-foundation>`
1. Log in to the `cf` CLI with an
   [`admin`](https://docs.pivotal.io/application-service/3-0/uaa/uaa-user-management.html#creating-admin-users)
   or
   [`admin_read_only`](https://docs.pivotal.io/application-service/3-0/uaa/uaa-user-management.html#admin-read-only)
   user or client: `cf login`
1. Download the collector and submitter: `wget https://github.com/Tanzu-Gerg/Tanzu-Telemetry-Standalone-Data-Collector/releases/download/v1.0.2/tanzu-telemetry-standalone-data-collector-1.0.2.tgz`
1. Extract the downloaded tar: `tar -xf tanzu-telemetry-standalone-data-collector-1.0.2.tgz`
1. `cd tanzu-telemetry-standalone-data-collector/`
1. Run the collector script: `./tanzu-telemetry-standalone-data-collector.py`

### Collector Output

Output from the collector script is written to `output.json` in your current
working directory. See the "Collected Data" section below for details on what
data is collected.

### Submitting Data

1. Locate your telemetry customer ID. Navigate to
   `https://<opsmanager-installation>/api/v0/deployed/products` and find the
   `guid` for the `p-bosh` product (it should match `p-bosh-<random id>`). This
   is your customer ID for telemetry submission.
1. Identify what platform you are running the submission executable on. For
   example, if you are running on Linux, your platform is `linux_x86-64`.
1. (Optional) Review what data will be submitted to the telemetry system (writes to stdout):
   `./<platform>/tanzu-telemetry-standalone-data-submitter --input output.json --customerId <customer-id> generate`)
1. Submit the collected data to the TAS telemetry
   system: `./<platform>/tanzu-telemetry-standalone-data-submitter --input output.json --customerId <customer-id> send`

### Clean Up

After the data is successfully submitted to TAS telemetry, you may delete the
output file, the collector, and the submitter. For example: `rm -r $HOME/tanzu-telemetry-standalone-data-collector*`

## Collected Data

Data collected for all apps with state `STARTED`:
- guid
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
- `springframework.boot.loader.JarLauncher`
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

To review additional documentation for what data is being collected, click
[here](https://docs.vmware.com/en/Tanzu-Application-Service-Standalone-Data-Collection-Scripts/1.0/data-collection-scripts/standalone-data-collection-script.html).

## Collector Configuration

Environment variables (set in the shell executing the collector script):

|Var|Effect|
|-|-|
| `ACCEPT_CEIP` | If set, automatically accept VMware Customer Experience Improvement Program data collection. |
| `ANON_BP_VARS` | If set, anonymize buildpack-related environment variables. |
| `BYPASS_ANON` | If set, do not anonymize fields. |

Usage example:
```sh
BYPASS_ANON=1 ./tanzu-telemetry-standalone-data-collector.py
```

## Collector Performance

Performance for a trial against a deployment seeded with 10,000 apps (NOT app
instances), when run on a bosh instance (jammy stemcell), using the procedure
described above:
- Execution time: ~40 minutes
- Memory consumption: ~110M
- CPU consumption: ~1.4% of 2.20GHz CPU
- Output file size: ~8.7M

## Collector Development

For testing (or running, I suppose) the collector script on Python 3.5 via the
included Dockerfile (requires Docker):

1. Navigate to the `Tanzu-Telemetry-Standalone-Data-Collector` directory
1. Get a Linux CF CLI in the directory. For example:
   ```
   $ wget https://packages.cloudfoundry.org/stable\?release\=linux64-binary\&version\=8.5.0\&source\=github-rel -O cf.tgz
   ...
   $ tar -xf cf.tgz
   ...
   $ mv cf8 cf
   ...
   ```
1. `docker build -t tanzu-telemetry-standalone-data-collector`
1. `docker run --env "CF_API=<cf API here>" --env "CF_USER=admin" --env "CF_PASSWORD=<admin password here>" tanzu-telemetry-standalone-data-collector`

The Dockerfile is based on Ubuntu Xenial, which should be similar to the Xenial stemcell.
