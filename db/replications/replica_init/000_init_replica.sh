#!/usr/bin/env bash
set -euo pipefail

echo "Initializing physical replica..."

# Remove empty init cluster
rm -rf ${PGDATA:?}/*

# Physical base backup from primary
pg_basebackup -h postgres -D "$PGDATA" -U travel -Fp -Xs -P -R

echo "Replica base backup completed!"
echo "standby.signal created. Replica ready."
