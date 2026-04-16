#!/bin/bash
# Multi-database initialization script for Postgres
# Creates databases and users for Censer ecosystem services
set -e
set -u

function create_user_and_database() {
    local database=$1
    local user=$2
    local password=${3:-$user}  # Default password = username

    echo "Creating database '$database' with user '$user'"
    psql -v ON_ERROR_STOP=1 --username "$POSTGRES_USER" <<-EOSQL
        CREATE USER $user WITH PASSWORD '$password';
        CREATE DATABASE $database;
        GRANT ALL PRIVILEGES ON DATABASE $database TO $user;
        \\c $database
        GRANT ALL ON SCHEMA public TO $user;
EOSQL
}

# Create databases for each service
create_user_and_database "stoat" "stoat"
create_user_and_database "discord_stoat_sync" "stoatsync"
create_user_and_database "unveil_dev" "unveil"
create_user_and_database "billing" "billing"

echo "✅ All databases created successfully"
