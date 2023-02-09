# buildpack-sniffer
Sniff out what buildpacks are in use (and how) on a given Cloud Foundry
deployment. This tool is intended to help understand how easy it will be to
migrate Cloud Foundry applications to v3 buildpacks.

## Usage

### Requirements

Currently, this script depends on the following (these may relax over time):
- Python 3.10+ (goal: Python 3.5+)
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
