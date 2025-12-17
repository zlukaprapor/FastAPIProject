#!/bin/bash
set -e

# Визначаємо які БД створювати на основі SHARD_ID
SHARD_ID=${SHARD_ID:-unknown}

case $SHARD_ID in
  0)
    DBS=("db_0" "db_1" "db_2" "db_3")
    ;;
  1)
    DBS=("db_4" "db_5" "db_6" "db_7")
    ;;
  2)
    DBS=("db_8" "db_9" "db_a" "db_b")
    ;;
  3)
    DBS=("db_c" "db_d" "db_e" "db_f")
    ;;
  *)
    echo "Unknown SHARD_ID: $SHARD_ID"
    exit 1
    ;;
esac

echo "Initializing databases on SHARD $SHARD_ID: ${DBS[@]}"

# Створюємо кожну БД та застосовуємо міграції
for db in "${DBS[@]}"; do
  echo "Creating database: $db"
  psql -v ON_ERROR_STOP=1 -U "$POSTGRES_USER" <<-EOSQL
    CREATE DATABASE $db;
    GRANT ALL PRIVILEGES ON DATABASE $db TO $POSTGRES_USER;
EOSQL

  echo "Applying migrations to $db"
  if [ -d /docker-entrypoint-migrations ]; then
    for sql_file in /docker-entrypoint-migrations/*.sql; do
      if [ -f "$sql_file" ]; then
        echo "  Applying: $sql_file"
        psql -v ON_ERROR_STOP=1 -U "$POSTGRES_USER" -d "$db" -f "$sql_file"
      fi
    done
  fi
done

echo "Shard initialization completed on SHARD $SHARD_ID"