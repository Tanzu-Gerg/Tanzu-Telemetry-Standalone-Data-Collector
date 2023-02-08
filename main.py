#!/usr/bin/env python3

import json
import subprocess

from types import SimpleNamespace

class AppLifecycle(SimpleNamespace):
    type: str
    buildpacks: list[str]

    def as_dict(self) -> dict:
       return self.__dict__


class Droplet(SimpleNamespace):
    buildpacks: list[dict[str, str]]

    def as_dict(self) -> dict:
       return self.__dict__


class App(SimpleNamespace):
    guid: str
    state: str
    lifecycle: AppLifecycle
    current_droplet: Droplet | None = None
    env: dict

    def as_dict(self) -> dict:
        return {
                "guid": self.guid,
                "state": self.state,
                "lifecycle": self.lifecycle.as_dict(),
                "current_droplet": self.current_droplet.as_dict(),
                "env": self.env,
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

    print("Apps:")
    print(json.dumps([ app.as_dict() for app in all_apps ]))


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
        total_app_pages = apps_pagination.get("total_pages")

        apps = parsed_apps_response.get("resources")
        parsed_apps = [
            App(
                guid=app.get("guid"),
                state=app.get("state"),
                lifecycle=_construct_lifecycle(app)
            )
            for app in apps
        ]
        all_apps = all_apps + parsed_apps

        current_app_page += 1

        if not apps_pagination.get("next"):
            break

    print("\n")
    return all_apps


def _construct_lifecycle(app: dict) -> AppLifecycle:
    lifecycle = app.get("lifecycle", {})
    return AppLifecycle(
            type=lifecycle.get("type"),
            buildpacks=lifecycle.get("data", {}).get("buildpacks") # TODO: Docker apps
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
        parsed_droplet_response = json.loads(droplet_response_raw) # TODO: 404 case
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
        parsed_env_response = json.loads(env_response_raw) # TODO: 404 case
        app.env = parsed_env_response
    print("\n")
    return all_apps


if __name__ == "__main__":
    main()
