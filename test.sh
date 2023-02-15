#!/usr/bin/env bash

set -e

cf api $CF_API --skip-ssl-validation
cf auth $CF_USER $CF_PASSWORD
./tanzu-telemetry-standalone-data-collector.py
cat ./output.json
