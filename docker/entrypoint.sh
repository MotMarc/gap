#!/bin/sh
set -eu

python scripts/manage_database.py upgrade
exec "$@"

