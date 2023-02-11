#!/usr/bin/env python3

import hashlib
import json
import subprocess

from os import environ
from types import SimpleNamespace
from typing import List, Dict, Optional

class AppLifecycle(SimpleNamespace):
    # type: str
    # buildpacks: List[str]
    # stack: str

    def as_dict(self) -> Dict:
       return self.__dict__


class Droplet(SimpleNamespace):
    # buildpacks: List[Dict[str, str]]

    def as_dict(self) -> Dict:
       return self.__dict__


class Service(SimpleNamespace):
    # label: str
    # tags: List[str]
    # name: str

    def as_dict(self) -> Dict:
       return self.__dict__


class Env(SimpleNamespace):
    # vcap_services: List[Service]
    # staging_env: List[str]
    # running_env: List[str]
    # environment_variables: List[str]

    def as_dict(self) -> Dict:
        return {
                "vcap_services": [service.as_dict() for service in self.vcap_services],
                "staging_env": self.staging_env,
                "running_env": self.running_env,
                "environment_variables": self.environment_variables,
                }

class App(SimpleNamespace):
    # guid: str
    # state: str
    # lifecycle: AppLifecycle
    # current_droplet: Optional[Droplet] = None
    # env: Optional[Env] = None

    def as_dict(self) -> Dict:
        return {
                "guid": self.guid,
                "state": self.state,
                "lifecycle": self.lifecycle.as_dict(),
                "current_droplet": self.current_droplet.as_dict() if self.current_droplet else None,
                "env": self.env.as_dict() if self.env else None,
                }

ALERT = """
====================================================================
 ALERT: You must target the desired environment with 'cf' CLI,
        logged in as an admin or admin_read_only user.
====================================================================
"""

PAGE_SIZE=5000
NO_ANON_JPB_VARS = [
        "JBP_DEFAULT_COMPONENTS",
        "JBP_CONFIG_COMPONENTS",
        "JBP_CONFIG_SPRING_AUTO_RECONFIGURATION",
        ]
ANON_JBP=environ.get("ANON_JBP")
BYPASS_ANON=environ.get("BYPASS_ANON")

def main():
    print(ALERT)
    all_apps = _fetch_apps()
    if len(all_apps):
        all_apps = _fetch_droplets(all_apps)
        all_apps = _fetch_env(all_apps)

    print("Generating output...")
    app_json = json.dumps([ app.as_dict() for app in all_apps ])

    print("Writing output...")
    with open("output.json", "w", encoding="utf-8") as f:
        f.writelines(app_json)

    print("Done!")


def _fetch_apps() -> List[App]:
    print("[Step 1/3] Fetching all apps...")

    current_app_page = 1
    total_app_pages = "1"
    all_apps = []
    while True:
        print("Fetching apps page " + str(current_app_page) + "/" + str(total_app_pages), end="\r")
        apps_response_raw = subprocess.run(
            ["cf", "curl", "/v3/apps?per_page=" + str(PAGE_SIZE) + ";page=" + str(current_app_page)],
            stdout=subprocess.PIPE,
            universal_newlines=True
        ).stdout

        parsed_apps_response = _parse_json(apps_response_raw)

        errors = parsed_apps_response.get("errors", None)
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
    lifecycle = app.get("lifecycle", {})
    return AppLifecycle(
            type=lifecycle.get("type", ""),
            buildpacks=lifecycle.get("data", {}).get("buildpacks", []),
            stack=lifecycle.get("data", {}).get("stack", ""),
            )


def _fetch_droplets(all_apps: List[App]) -> List[App]:
    print("[Step 2/3] Fetching droplets...")
    for index, app in enumerate(all_apps):
        print("Fetching droplet " + str(index + 1) + "/" + str(len(all_apps)), end="\r")
        droplet_response_raw = subprocess.run(
            ["cf", "curl", "/v3/apps/" + str(app.guid) + "/droplets/current"],
            stdout=subprocess.PIPE,
            universal_newlines=True
        ).stdout
        parsed_droplet_response = _parse_json(droplet_response_raw)
        app.current_droplet = Droplet(buildpacks=parsed_droplet_response.get('buildpacks', []))
    print("\n")
    return all_apps


def _fetch_env(all_apps: List[App]) -> List[App]:
    print("[Step 3/3] Fetching environment variables...")
    for index, app in enumerate(all_apps):
        print("Fetching env " + str(index + 1) + "/" + str(len(all_apps)), end="\r")
        env_response_raw = subprocess.run(
            ["cf", "curl", "/v3/apps/" + str(app.guid) + "/env"],
            stdout=subprocess.PIPE,
            universal_newlines=True
        ).stdout
        parsed_env_response = _parse_json(env_response_raw)
        app.env = _construct_env(parsed_env_response)
    print("\n")
    return all_apps


def _construct_env(env: Dict) -> Env:
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


def _construct_services(vcap_services: Dict) -> List[Service]:
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


def _parse_json(raw_response: str) -> dict:
    try:
        parsed_response = json.loads(raw_response)
        return parsed_response
    except Exception as e:
        print("\n[Error] Failed to parse:\n" + str(raw_response) + "\nas JSON.")
        raise e


def _handle_errors(parsed_response: dict) -> None:
        errors = parsed_response.get("errors", None)
        if errors:
            print("\nEncountered API errors: ")
            print(errors)


def _flatten_variables(vars: Optional[Dict]) -> List[str]:
    flattened_vars = []
    if vars:
        for key, val in vars.items():
            if ((not ANON_JBP) and (key in NO_ANON_JPB_VARS)):
                flattened_vars.append(key + "=" + val)
            else:
                flattened_vars.append(_anonymize(key))
    return flattened_vars


def _anonymize_list(list_of_str: List[str]) -> str:
    return [_anonymize(string) for string in list_of_str]


def _anonymize(string: str) -> str:
    if BYPASS_ANON: return string
    return hashlib.sha256(bytes(string, "utf-8")).hexdigest()


if __name__ == "__main__":
    main()
