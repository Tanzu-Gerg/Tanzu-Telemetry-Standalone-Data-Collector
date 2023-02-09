#!/usr/bin/env python3

import json
import subprocess

from types import SimpleNamespace

class AppLifecycle(SimpleNamespace):
    type: str
    buildpacks: list[str]
    stack: str

    def as_dict(self) -> dict:
       return self.__dict__


class Droplet(SimpleNamespace):
    buildpacks: list[dict[str, str]]

    def as_dict(self) -> dict:
       return self.__dict__


class Env(SimpleNamespace):
    vcap_services: list[str]
    staging_env_json: list[str]
    running_env_json: list[str]
    environment_variables: list[str]

    def as_dict(self) -> dict:
       return self.__dict__


class App(SimpleNamespace):
    guid: str
    state: str
    lifecycle: AppLifecycle
    current_droplet: Droplet | None = None
    env: Env | None = None

    def as_dict(self) -> dict:
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
 ALERT: You must target the desired environment with 'cf' CLI v8,
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


def _fetch_apps() -> list[App]:
    print("Fetching all apps...")

    current_app_page = 1
    total_app_pages = "1"
    all_apps = []
    while True:
        print(f"Fetching apps page {current_app_page}/{total_app_pages}", end="\r")
        apps_response_raw = subprocess.run(
            ["cf", "curl", f"/v3/apps?per_page={PAGE_SIZE};page={current_app_page}"],
            stdout=subprocess.PIPE,
            text=True
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


def _construct_lifecycle(app: dict) -> AppLifecycle:
    lifecycle = app.get("lifecycle", {})
    return AppLifecycle(
            type=lifecycle.get("type", ""),
            buildpacks=lifecycle.get("data", {}).get("buildpacks", []),
            stack=lifecycle.get("data", {}).get("stack", ""),
            )


def _fetch_droplets(all_apps: list[App]) -> list[App]:
    print("Fetching droplets...")
    for index, app in enumerate(all_apps):
        print(f"Fetching droplet {index + 1}/{len(all_apps)}", end="\r")
        droplet_response_raw = subprocess.run(
            ["cf", "curl", f"/v3/apps/{app.guid}/droplets/current"],
            stdout=subprocess.PIPE,
            text=True
        ).stdout
        parsed_droplet_response = json.loads(droplet_response_raw)
        app.current_droplet = Droplet(buildpacks=parsed_droplet_response.get('buildpacks', []))
    print("\n")
    return all_apps


def _fetch_env(all_apps: list[App]) -> list[App]:
    print("Fetching environment variables...")
    for index, app in enumerate(all_apps):
        print(f"Fetching env {index + 1}/{len(all_apps)}", end="\r")
        env_response_raw = subprocess.run(
            ["cf", "curl", f"/v3/apps/{app.guid}/env"],
            stdout=subprocess.PIPE,
            text=True
        ).stdout
        parsed_env_response = json.loads(env_response_raw)
        app.env = _construct_env(parsed_env_response)
    print("\n")
    return all_apps

def _construct_env(env: dict) -> Env:
    vcap_services = env.get('system_env_json', {}).get('VCAP_SERVICES', {})
    staging_env_json = env.get('staging_env_json', {})
    running_env_json = env.get('running_env_json', {})
    environment_variables = env.get('environment_variables', {})
    return Env(
            vcap_services=_noneable_keys(vcap_services),
            staging_env_json=_noneable_keys(staging_env_json),
            running_env_json=_noneable_keys(running_env_json),
            environment_variables=_noneable_keys(environment_variables),
            )

def _noneable_keys(vars: dict | None) -> list[str]:
    return list(vars.keys()) if vars else []


if __name__ == "__main__":
    main()
