#!/usr/bin/env python3

import json
import subprocess

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
    # staging_env_json: List[str]
    # running_env_json: List[str]
    # environment_variables: List[str]

    def as_dict(self) -> Dict:
        return {
                "vcap_services": [service.as_dict() for service in self.vcap_services],
                "staging_env_json": self.staging_env_json,
                "running_env_json": self.running_env_json,
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


PAGE_SIZE=5000

def main():
    print("""
====================================================================
 ALERT: You must target the desired environment with 'cf' CLI,
        logged in as an admin or admin_read_only user.
====================================================================
""")
    all_apps = _fetch_apps()
    all_apps = _fetch_droplets(all_apps)
    all_apps = _fetch_env(all_apps)

    print("Generating output...")
    app_json = json.dumps([ app.as_dict() for app in all_apps ])

    print("Writing output...")
    with open("output.json", "w", encoding="utf-8") as f:
        f.writelines(app_json)

    print("Done!")


def _fetch_apps() -> List[App]:
    print("Fetching all apps...")

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

        parsed_apps_response = json.loads(apps_response_raw)
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

    print("\n")
    return all_apps


def _construct_lifecycle(app: Dict) -> AppLifecycle:
    lifecycle = app.get("lifecycle", {})
    return AppLifecycle(
            type=lifecycle.get("type", ""),
            buildpacks=lifecycle.get("data", {}).get("buildpacks", []),
            stack=lifecycle.get("data", {}).get("stack", ""),
            )


def _fetch_droplets(all_apps: List[App]) -> List[App]:
    print("Fetching droplets...")
    for index, app in enumerate(all_apps):
        print("Fetching droplet " + str(index + 1) + "/" + str(len(all_apps)), end="\r")
        droplet_response_raw = subprocess.run(
            ["cf", "curl", "/v3/apps/" + str(app.guid) + "/droplets/current"],
            stdout=subprocess.PIPE,
            universal_newlines=True
        ).stdout
        parsed_droplet_response = json.loads(droplet_response_raw)
        app.current_droplet = Droplet(buildpacks=parsed_droplet_response.get('buildpacks', []))
    print("\n")
    return all_apps


def _fetch_env(all_apps: List[App]) -> List[App]:
    print("Fetching environment variables...")
    for index, app in enumerate(all_apps):
        print("Fetching env " + str(index + 1) + "/" + str(len(all_apps)), end="\r")
        env_response_raw = subprocess.run(
            ["cf", "curl", "/v3/apps/" + str(app.guid) + "/env"],
            stdout=subprocess.PIPE,
            universal_newlines=True
        ).stdout
        parsed_env_response = json.loads(env_response_raw)
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
            staging_env_json=_noneable_keys(staging_env_json),
            running_env_json=_noneable_keys(running_env_json),
            environment_variables=_noneable_keys(environment_variables),
            )


def _construct_services(vcap_services: Dict) -> List[Service]:
    if vcap_services:
        all_services = []
        for bindings in vcap_services.values():
            for binding in bindings:
                all_services.append(
                    Service(
                        name=binding.get("name", ""),
                        label=binding.get("label", ""),
                        tags=binding.get("tags", []),
                        )
                )
        return all_services
    else:
        return []


def _noneable_keys(vars: Optional[Dict]) -> List[str]:
    return list(vars.keys()) if vars else []


if __name__ == "__main__":
    main()
