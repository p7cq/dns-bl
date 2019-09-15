#!/bin/bash

SCRIPT_DIR=$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)
export DNSBL_HOME=$(dirname ${SCRIPT_DIR})
/usr/bin/python3 ${DNSBL_HOME}/lib/dnsbl.py
