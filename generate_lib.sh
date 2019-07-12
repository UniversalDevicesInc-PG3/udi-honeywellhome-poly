#!/usr/bin/env bash

openapi-generator generate -c codegen-config.json -i honeywellhome.api.yaml -g python -o sdk

rm -r honeywell_home
mv sdk/honeywell_home honeywell_home
rm -r sdk
