#!/bin/bash
# Runs once, on the first start of an empty database volume.
# Creates one schema + one login role per service. Each role owns only its own schema,
# so neither service can read the other's data (architecture: service independence rules).
# Also creates a separate test database where each role may create its own throwaway schema.
set -euo pipefail

TEST_DB="${POSTGRES_DB}_test"

psql -v ON_ERROR_STOP=1 --username "$POSTGRES_USER" --dbname "$POSTGRES_DB" \
  -v invoice_pw="$INVOICE_DB_PASSWORD" \
  -v contract_pw="$CONTRACT_DB_PASSWORD" \
  -v test_db="$TEST_DB" <<'EOSQL'
CREATE ROLE invoice_svc LOGIN PASSWORD :'invoice_pw';
CREATE ROLE contract_svc LOGIN PASSWORD :'contract_pw';

REVOKE ALL ON DATABASE :"DBNAME" FROM PUBLIC;
REVOKE ALL ON SCHEMA public FROM PUBLIC;
GRANT CONNECT ON DATABASE :"DBNAME" TO invoice_svc, contract_svc;

CREATE SCHEMA invoices AUTHORIZATION invoice_svc;
CREATE SCHEMA contracts AUTHORIZATION contract_svc;

CREATE DATABASE :"test_db";
EOSQL

psql -v ON_ERROR_STOP=1 --username "$POSTGRES_USER" --dbname "$TEST_DB" <<'EOSQL'
REVOKE ALL ON DATABASE :"DBNAME" FROM PUBLIC;
REVOKE ALL ON SCHEMA public FROM PUBLIC;
GRANT CONNECT, CREATE ON DATABASE :"DBNAME" TO invoice_svc, contract_svc;
EOSQL
