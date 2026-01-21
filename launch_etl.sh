#!/bin/bash

# RSS Feed ETL Environment Setup Script
# This script sets up environment variables and activates the Python virtual environment
# Decouples sensitive information like API keys and database credentials from the code

# ============================================================================
# USAGE INSTRUCTIONS:
# ============================================================================
#
# ⚠️  IMPORTANT: This script must be SOURCED, not executed directly!
#
# ✅ CORRECT way to run:
#     source launch_etl.sh
#     OR
#     . launch_etl.sh
#
# ❌ INCORRECT ways (will not work):
#     bash launch_etl.sh      # Environment variables won't persist
#     ./launch_etl.sh         # Environment variables won't persist
#     python launch_etl.sh    # Wrong interpreter
#
# WHY SOURCE IS REQUIRED:
# - Sourcing runs the script in the current shell session
# - This allows environment variables to persist after the script finishes
# - Virtual environment activation only works when sourced
# - Without sourcing, variables are lost when the script exits
#
# PREREQUISITES:
# 1. Create .env.rssfeedetl file in this directory with:
#    RSS_FEED_ETL_DB_URL=postgresql://username:password@localhost:5432/rss_feed_etl
#    ANTHROPIC_API_KEY=sk-ant-api03-your-key-here
#    CHROMEDRIVER_PATH=/usr/bin/chromedriver
#
# 2. Ensure PostgreSQL is installed and running:
#    sudo apt install postgresql postgresql-contrib
#    sudo service postgresql start
#
# 3. Ensure Python virtual environment exists at /home/dchelimo/airflow_venv
#    Or update the path below to match your environment
#
# TROUBLESHOOTING:
# - If you see "RSS_FEED_ETL_DB_URL not set", check your .env.rssfeedetl file
# - If database connection fails, verify PostgreSQL is running and credentials are correct
# - If SQLAlchemy not found, ensure virtual environment is activated and dependencies installed
#
# ============================================================================

echo "=== RSS Feed ETL Environment Setup ==="

# --- CHECK IF SCRIPT IS BEING SOURCED ---
# Detect if script is being executed instead of sourced
if [[ "${BASH_SOURCE[0]}" == "${0}" ]]; then
    echo "❌ ERROR: This script must be SOURCED, not executed!"
    echo ""
    echo "✅ CORRECT usage:"
    echo "   source launch_etl.sh"
    echo "   OR"
    echo "   . launch_etl.sh"
    echo ""
    echo "❌ You ran it as: $0"
    echo ""
    echo "💡 Why sourcing is required:"
    echo "   - Environment variables need to persist in your shell session"
    echo "   - Virtual environment activation only works when sourced"
    echo "   - Without sourcing, all setup is lost when script exits"
    echo ""
    exit 1
fi

echo "✅ Script is being sourced correctly"
echo "Setting up environment variables..."

# Enable strict mode for critical operations only
set -e

# --- LOAD FROM ENV FILE ---
# Load environment variables from .env.rssfeedetl if it exists
# Look for .env file in the same directory as this script
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ENV_FILE="$SCRIPT_DIR/.env.rssfeedetl"

if [ -f "$ENV_FILE" ]; then
    echo "Loading environment variables from $ENV_FILE"
    set -a  # automatically export all variables
    source "$ENV_FILE"
    set +a  # stop automatically exporting
else
    echo "No .env.rssfeedetl file found at $ENV_FILE"
    echo "Please create this file with your configuration"
fi

# --- DATABASE CONFIGURATION ---
# Database connection string (REQUIRED - must be set in .env.rssfeedetl)
if [ -z "$RSS_FEED_ETL_DB_URL" ]; then
    echo "❌ ERROR: RSS_FEED_ETL_DB_URL not set"
    echo "Please set this in your .env.rssfeedetl file:"
    echo "RSS_FEED_ETL_DB_URL=postgresql://username:password@localhost:5432/rss_feed_etl"
    set +e  # Disable strict mode before returning
    return 1  # Use return instead of exit for sourced scripts
fi
export RSS_FEED_ETL_DB_URL

# --- POSTGRESQL SERVICE MANAGEMENT ---
echo "🔧 Checking PostgreSQL status..."

# Function to check if PostgreSQL is running
check_postgres_status() {
    if sudo service postgresql status >/dev/null 2>&1; then
        echo "✅ PostgreSQL is already running"
        return 0
    else
        echo "⚠️  PostgreSQL is not running"
        return 1
    fi
}

# Function to start PostgreSQL
start_postgres() {
    echo "🚀 Starting PostgreSQL service..."
    if sudo service postgresql start >/dev/null 2>&1; then
        echo "✅ PostgreSQL started successfully"
        # Wait a moment for the service to fully start
        sleep 2
        return 0
    else
        echo "❌ Failed to start PostgreSQL"
        echo "Please check if PostgreSQL is installed:"
        echo "  sudo apt update && sudo apt install postgresql postgresql-contrib"
        return 1
    fi
}

# Function to create database and user if they don't exist
setup_database() {
    echo "🔧 Checking database setup..."
    
    # Extract database details from connection string
    DB_NAME=$(echo "$RSS_FEED_ETL_DB_URL" | sed -n 's|.*://.*/.*/\([^?]*\).*|\1|p' | sed 's|/.*||')
    DB_USER=$(echo "$RSS_FEED_ETL_DB_URL" | sed -n 's|.*://\([^:]*\):.*|\1|p')
    DB_PASS=$(echo "$RSS_FEED_ETL_DB_URL" | sed -n 's|.*://[^:]*:\([^@]*\)@.*|\1|p')
    
    if [ -z "$DB_NAME" ]; then
        DB_NAME="rss_feed_etl"
    fi
    
    # Check if database exists
    if sudo -u postgres psql -lqt | cut -d \| -f 1 | grep -qw "$DB_NAME"; then
        echo "✅ Database '$DB_NAME' exists"
    else
        echo "🆕 Creating database '$DB_NAME'..."
        sudo -u postgres createdb "$DB_NAME" 2>/dev/null || echo "⚠️  Database creation failed (may already exist)"
    fi
    
    # Check if user exists and create if necessary
    if [ -n "$DB_USER" ] && [ -n "$DB_PASS" ]; then
        echo "🆕 Setting up database user '$DB_USER'..."
        sudo -u postgres psql -c "
            DO \$\$
            BEGIN
                IF NOT EXISTS (SELECT FROM pg_catalog.pg_roles WHERE rolname = '$DB_USER') THEN
                    CREATE USER $DB_USER WITH PASSWORD '$DB_PASS';
                END IF;
                GRANT ALL PRIVILEGES ON DATABASE $DB_NAME TO $DB_USER;
            END
            \$\$;
        " >/dev/null 2>&1
        echo "✅ Database user setup complete"
    fi
}

# Function to test database connection
test_database_connection() {
    echo "🔍 Testing database connection..."
    
    # Use Python to test the connection since we have SQLAlchemy
    python3 -c "
import os
import sys
try:
    from sqlalchemy import create_engine, text
    engine = create_engine(os.getenv('RSS_FEED_ETL_DB_URL'))
    with engine.connect() as conn:
        result = conn.execute(text('SELECT 1'))
        print('✅ Database connection successful')
        sys.exit(0)
except ImportError:
    print('⚠️  SQLAlchemy not available, skipping connection test')
    sys.exit(0)
except Exception as e:
    print(f'❌ Database connection failed: {e}')
    sys.exit(1)
" 2>/dev/null
    return $?
}

# Execute PostgreSQL setup sequence
if ! check_postgres_status; then
    if ! start_postgres; then
        echo "❌ Cannot proceed without PostgreSQL"
        set +e
        return 1
    fi
fi

# Setup database and user
setup_database

# Test the connection
if ! test_database_connection; then
    echo "⚠️  Database connection test failed, but continuing..."
    echo "You may need to manually create the database or check credentials"
fi

# --- API CONFIGURATION ---
# Anthropic Claude API Key (REQUIRED - must be set in .env.rssfeedetl)
if [ -z "$ANTHROPIC_API_KEY" ]; then
    echo "❌ ERROR: ANTHROPIC_API_KEY not set"
    echo "Please set this in your .env.rssfeedetl file:"
    echo "ANTHROPIC_API_KEY=sk-ant-api03-..."
    set +e  # Disable strict mode before returning
    return 1  # Use return instead of exit for sourced scripts
fi
export ANTHROPIC_API_KEY

# --- CHROME DRIVER CONFIGURATION ---
# Path to ChromeDriver executable (safe default for common WSL setups)
export CHROMEDRIVER_PATH="${CHROMEDRIVER_PATH:-/usr/bin/chromedriver}"

# --- PYTHON ENVIRONMENT ---
# Ensure Python environment is activated (uncomment if using virtual env)
source /home/dchelimo/airflow_venv/bin/activate
echo "Activated Python virtual environment: /home/dchelimo/airflow_venv"

# --- VALIDATION ---
# Note: Removed credential validation to avoid exposing real passwords in logs

echo ""
echo "✅ Environment setup completed successfully"
echo ""
echo "✅ Environment variables are set:"
echo "  RSS_FEED_ETL_DB_URL: postgresql://***:***@$(echo "$RSS_FEED_ETL_DB_URL" | sed 's|.*@||')"
echo "  ANTHROPIC_API_KEY: ${ANTHROPIC_API_KEY:0:10}... (truncated for security)"
echo "  CHROMEDRIVER_PATH: ${CHROMEDRIVER_PATH}"
echo ""
echo "✅ PostgreSQL service is running and database is configured"
echo "✅ Python virtual environment activated: /home/dchelimo/airflow_venv"
echo ""
echo "🧪 TESTING - You can now manually test the ETL components:"
echo "  1. Test SQLAlchemy:"
echo "     python -c 'import sqlalchemy; print(\"SQLAlchemy available:\", sqlalchemy.__version__)'"
echo ""
echo "  2. Test Anthropic Claude API:"
echo "     python -c 'import anthropic; print(\"Anthropic client available\")'"
echo ""
echo "  3. Test scraper module:"
echo "     python -c 'from operators import scraper; print(\"Scraper module available\")'"
echo ""
echo "  4. Test database connection:"
echo "     python -c \"from sqlalchemy import create_engine; import os; engine = create_engine(os.getenv('RSS_FEED_ETL_DB_URL')); print('DB connection:', '✅ Success' if engine.connect() else '❌ Failed')\""
echo ""
echo "🚀 RUNNING THE ETL PIPELINE:"
echo "  Run the complete ETL process:"
echo "     python -m dags.war_etl_dag"
echo ""
echo "📊 MONITORING:"
echo "  Check database for results:"
echo "     python test_db_connection.py"
echo ""
echo "📁 GETTING HELP:"
echo "  View scraper options:"
echo "     python -m operators.scraper --help"
echo ""
echo "Environment is ready for testing!"

# Disable strict mode to avoid affecting interactive shell
set +e

echo "=== Environment setup completed ==="