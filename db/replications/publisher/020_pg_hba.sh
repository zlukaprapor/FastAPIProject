#!/usr/bin/env bash
set -euo pipefail
# Дозволити subscriber підключатися по паролю до всіх баз під користувачем repuser
echo "host all repuser 0.0.0.0/0 md5" >> "${PGDATA}/pg_hba.conf"