#!/usr/bin/env bash
set -euo pipefail

echo "host replication travel 0.0.0.0/0 md5" >> "$PGDATA/pg_hba.conf"
