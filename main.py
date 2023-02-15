#!/usr/bin/env python3

import hashlib
import json
import subprocess

from os import environ
from types import SimpleNamespace
from typing import List, Dict, Optional


class AppLifecycle(SimpleNamespace):
    """
    type: str
    buildpacks: List[str]
    stack: str
    """

    def as_dict(self) -> Dict:
        """Define how app lifecycles will be rendered as JSON."""
        return self.__dict__


class Droplet(SimpleNamespace):
    """
    buildpacks: List[Dict[str, str]]
    """

    def as_dict(self) -> Dict:
        """Define how droplets will be rendered as JSON."""
        return self.__dict__


class Service(SimpleNamespace):
    """
    label: str
    tags: List[str]
    name: str
    """

    def as_dict(self) -> Dict:
        """Define how services will be rendered as JSON."""
        return self.__dict__


class Env(SimpleNamespace):
    """
    vcap_services: List[Service]
    staging_env: List[str]
    running_env: List[str]
    environment_variables: List[str]
    """

    def as_dict(self) -> Dict:
        """Define how environment variables will be rendered as JSON."""
        return {
                "vcap_services": [service.as_dict() for service in self.vcap_services],
                "staging_env": self.staging_env,
                "running_env": self.running_env,
                "environment_variables": self.environment_variables,
                }


class Process(SimpleNamespace):
    """
    command_fragments: List(str)
    """

    def as_dict(self) -> Dict:
        """Define how processes will be rendered as JSON."""
        return self.__dict__


class App(SimpleNamespace):
    """
    guid: str
    state: str
    lifecycle: AppLifecycle
    current_droplet: Optional[Droplet] = None
    env: Optional[Env] = None
    process: Optional[Process] = None
    """

    def as_dict(self) -> Dict:
        """Define how Apps will be rendered as JSON."""
        return {
                "guid": self.guid,
                "state": self.state,
                "lifecycle": self.lifecycle.as_dict(),
                "current_droplet": self.current_droplet.as_dict() if self.current_droplet else None,
                "env": self.env.as_dict() if self.env else None,
                "process": self.process.as_dict() if self.process else None,
                }


ALERT = """
====================================================================
 ALERT: You must target the desired environment with 'cf' CLI,
        logged in as an admin or admin_read_only user.
====================================================================
"""

# Number of resources to fetch per page on the API
PAGE_SIZE = 5000

# Environment variables to not anonymize (see below)
NO_ANON_VARS = [
        "BP_PIP_VERSION",  # used by Python Buildpack
        "CACHE_NUGET_PACKAGES",  # used by .NET Core Buildpack
        "EXTENSIONS",  # used by PHP Buildpack
        "GOVERSION",  # used by Go Buildpack
        "JBP_CONFIG_COMPONENTS",  # used by Java Buildpack
        "JBP_CONFIG_SPRING_AUTO_RECONFIGURATION",  # used by Java Buildpack
        "JBP_DEFAULT_COMPONENTS",  # used by Java Buildpack
        "NODE_ENV",  # used by Node.js Buildpack
        "WEBDIR",  # used by PHP Buildpack
        "WEB_CONCURRENCY",  # used by Node.js Buildpack
        "WEB_MEMORY",  # used by Node.js Buildpack
        "WEB_SERVER",  # used by PHP Buildpack
        ]

# Start command fragments to collect (se below)
COMMAND_FRAGMENTS = [
        "open_jdk_jre/bin/java ",
        "springframework.boot.lader.JarLauncher",
        "groovy/bin/groovy ",
        "spring_boot_cli/bin/spring run",
        "tomcat/bin/catalina.sh run",
        ]

# If set, anonymize environment variables from NO_ANON_VARS
ANON_BP_VARS = environ.get("ANON_BP_VARS")

# If set, anonymize nothing
BYPASS_ANON = environ.get("BYPASS_ANON")


def main():
    """Collect all visible apps, then fetch the current droplet, environment
    variables, and web process for each app. Render the resulting data as JSON
    and write to an output file in the current directory.
    """
    print(ALERT)
    all_apps = _fetch_apps()
    if len(all_apps):
        all_apps = _fetch_droplets(all_apps)
        all_apps = _fetch_env(all_apps)
        all_apps = _fetch_processes(all_apps)

    print("Generating output...")
    app_json = json.dumps([app.as_dict() for app in all_apps])

    print("Writing output...")
    with open("output.json", "w", encoding="utf-8") as f:
        f.writelines(app_json)

    print("Done!")


def _fetch_apps() -> List[App]:
    """Fetch the first page of apps from the API (via 'cf curl') and build a
    list of App objects containing guid, state, and lifecycle. Then repeat for
    each page of apps, until there are no additional pages of apps.
    """
    print("[Step 1/4] Fetching all apps...")

    current_app_page = 1
    total_app_pages = "1"
    all_apps = []
    while True:
        print("Fetching apps page " + str(current_app_page) + "/" + str(total_app_pages), end="\r")
        apps_response_raw = subprocess.run(
            ["cf", "curl", "/v3/apps?per_page=" + str(PAGE_SIZE) + ";page=" + str(current_app_page)],
            check=True,
            stdout=subprocess.PIPE,
            universal_newlines=True
        ).stdout

        parsed_apps_response = _parse_json(apps_response_raw)

        _handle_errors(parsed_apps_response)
        apps_pagination = parsed_apps_response.get("pagination", {})
        total_app_pages = apps_pagination.get("total_pages", "?")

        apps = parsed_apps_response.get("resources", [])
        parsed_apps = [
            App(
                guid=app.get("guid", ""),
                state=app.get("state", ""),
                lifecycle=_construct_lifecycle(app)
            )
            for app in apps
        ]
        all_apps = all_apps + parsed_apps

        current_app_page += 1

        if not apps_pagination.get("next", None):
            break

    print("\nFetched " + str(len(all_apps)) + " apps.\n")
    return all_apps


def _construct_lifecycle(app: Dict) -> AppLifecycle:
    """Convert API app dict into AppLifecycle object, containing lifecycle
    type, configured buildpacks, and stack.
    """
    lifecycle = app.get("lifecycle", {})
    return AppLifecycle(
            type=lifecycle.get("type", ""),
            buildpacks=lifecycle.get("data", {}).get("buildpacks", []),
            stack=lifecycle.get("data", {}).get("stack", ""),
            )


def _fetch_droplets(all_apps: List[App]) -> List[App]:
    """For each app, fetch that app's current droplet via
    '/v3/apps/:guid/droplets/current'. Use the resulting JSON to construct a
    Droplet object, containing the buildpacks detected during staging. Add the
    constructed Droplet object to the corresponding App object.
    """
    print("[Step 2/4] Fetching droplets...")
    for index, app in enumerate(all_apps):
        print("Fetching droplet " + str(index + 1) + "/" + str(len(all_apps)), end="\r")
        droplet_response_raw = subprocess.run(
            ["cf", "curl", "/v3/apps/" + str(app.guid) + "/droplets/current"],
            check=True,
            stdout=subprocess.PIPE,
            universal_newlines=True
        ).stdout
        parsed_droplet_response = _parse_json(droplet_response_raw)
        app.current_droplet = Droplet(buildpacks=parsed_droplet_response.get("buildpacks", []))
    print("\n")
    return all_apps


def _fetch_env(all_apps: List[App]) -> List[App]:
    """For each app, fetch that app's environment variables via
    '/v3/apps/:guid/env'. This will include app-level environment variables, in
    addition to environment variable groups and VCAP_SERVICES. Use the
    resulting JSON to construct an Env object containing these environment
    variables. Add the constructed Env object to the corresponding App object.
    """
    print("[Step 3/4] Fetching environment variables...")
    for index, app in enumerate(all_apps):
        print("Fetching env " + str(index + 1) + "/" + str(len(all_apps)), end="\r")
        env_response_raw = subprocess.run(
            ["cf", "curl", "/v3/apps/" + str(app.guid) + "/env"],
            check=True,
            stdout=subprocess.PIPE,
            universal_newlines=True
        ).stdout
        parsed_env_response = _parse_json(env_response_raw)
        app.env = _construct_env(parsed_env_response)
    print("\n")
    return all_apps


def _construct_env(env: Dict) -> Env:
    """Convert API env dict into Env object, containing environment variables
    from VCAP_SERVICES, staging environment variable groups, running
    environment variable groups, and environment variables configured directly
    on the app. Environment variables are mostly anonymized, as described below.
    """
    vcap_services = env.get('system_env_json', {}).get('VCAP_SERVICES', {})
    staging_env_json = env.get('staging_env_json', {})
    running_env_json = env.get('running_env_json', {})
    environment_variables = env.get('environment_variables', {})
    return Env(
            vcap_services=_construct_services(vcap_services),
            staging_env=_flatten_variables(staging_env_json),
            running_env=_flatten_variables(running_env_json),
            environment_variables=_flatten_variables(environment_variables),
            )


def _construct_services(vcap_services: Optional[Dict]) -> List[Service]:
    """Collect name, label, and tags for each service binding in VCAP_SERVICES.
    All service fields are sha256-anonymized.
    """
    if vcap_services:
        all_services = []
        for bindings in vcap_services.values():
            for binding in bindings:
                all_services.append(
                    Service(
                        name=_anonymize(binding.get("name", "")),
                        label=_anonymize(binding.get("label", "")),
                        tags=_anonymize_list(binding.get("tags", [])),
                        )
                )
        return all_services
    else:
        return []


def _flatten_variables(variables: Optional[Dict]) -> List[str]:
    """Convert environment variable dict into a list of strings.

    For most environment variables, only environment variable keys
    (NOT values) are collected in an sha256-anonymized list.

    A selection of buildpack-configuration environment variables
    (defined in NO_ANON_VARS, above) are NOT anonymized AND
    values are collected in addition to keys.

    The buildpack-configuration environment variables can be anonymized by
    setting the ANON_BP_VARS environment variable in the execution shell when
    running this script.
    """
    flattened_vars = []
    if variables:
        for key, val in variables.items():
            if ((not ANON_BP_VARS) and (key in NO_ANON_VARS)):
                flattened_vars.append(key + "=" + val)
            else:
                flattened_vars.append(_anonymize(key))
    return flattened_vars


def _anonymize_list(list_of_str: List[str]) -> List[str]:
    """Anonymize all strings in a list."""
    return [_anonymize(string) for string in list_of_str]


def _anonymize(string: str) -> str:
    """Anonymize a string by taking a sha256 digest of the string. The
    resulting anonymized string can NOT be converted back to the original
    string. However, known strings can be identified, because the digest will
    be the same.

    For example, the string "foo" always anonymizes into
    "2c26b46b68ffc68ff99b453c1d30413413422d706483bfa0f98a5e886266e7ae", so someone
    looking for "foo" could identify it by searching for the known digest.
    However, someone could NOT recover the string "foo" from the digest alone.

    If the BYPASS_ANON environment variable is set in the execution shell when
    running this script, then values will not be anonymized.
    """
    if BYPASS_ANON:
        return string
    return hashlib.sha256(bytes(string, "utf-8")).hexdigest()


def _fetch_processes(all_apps: List[App]) -> List[App]:
    """For each app, fetch that app's web process via
    '/v3/apps/:guid/processes/web'. Use the resulting JSON to construct a
    Process object, containing matching start command fragments. Add the
    constructed Process object to the corresponding App object.
    """
    print("[Step 4/4] Fetching processes...")
    for index, app in enumerate(all_apps):
        print("Fetching process " + str(index + 1) + "/" + str(len(all_apps)), end="\r")
        process_response_raw = subprocess.run(
            ["cf", "curl", "/v3/apps/" + str(app.guid) + "/processes/web"],
            check=True,
            stdout=subprocess.PIPE,
            universal_newlines=True
        ).stdout
        parsed_process_response = _parse_json(process_response_raw)
        app.process = _construct_process(parsed_process_response)
    print("\n")
    return all_apps


def _construct_process(process: Dict) -> Process:
    """Convert API process dict into Process object, containing matching start
    command fragments from COMMAND_FRAGMENTS, defined above. Only the matching
    start command fragments are recorded; the rest of the start command is NOT
    recorded.
    """
    command = process.get('command', "")
    matching_command_fragments = [fragment for fragment in COMMAND_FRAGMENTS if fragment in command]
    return Process(
            command_fragments=matching_command_fragments
            )


def _parse_json(raw_response: str) -> dict:
    """Parse API response JSON and return the resulting dict."""
    try:
        parsed_response = json.loads(raw_response)
        return parsed_response
    except Exception as e:
        print("\n[Error] Failed to parse:\n" + str(raw_response) + "\nas JSON.")
        raise e


def _handle_errors(parsed_response: dict) -> None:
    """Surface any errors returned from the API."""
    errors = parsed_response.get("errors", None)
    if errors:
        print("\nEncountered API errors: ")
        print(errors)


if __name__ == "__main__":
    main()
