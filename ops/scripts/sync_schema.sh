#!/bin/bash
# =============================================================================
# Schema Sync Script for TradePulse IQ
# =============================================================================
# Synchronizes local schema.sql with production database
# Usage: ./ops/scripts/sync_schema.sh [--dry-run] [--force]
# =============================================================================

set -e  # Exit on error

# Color output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
SERVER="${SERVER:-138.68.245.159}"
SSH_USER="${SSH_USER:-root}"
DB_NAME="${DB_NAME:-trad}"
DB_USER="${DB_USER:-postgres}"
SCHEMA_FILE="sql/schema.sql"
BACKUP_DIR="/tmp/trad_backups"

# Parse arguments
DRY_RUN=false
FORCE=false

for arg in "$@"; do
    case $arg in
        --dry-run)
            DRY_RUN=true
            shift
            ;;
        --force)
            FORCE=true
            shift
            ;;
        --help|-h)
            echo "Usage: $0 [OPTIONS]"
            echo ""
            echo "Options:"
            echo "  --dry-run    Show what would be done without making changes"
            echo "  --force      Skip confirmation prompts"
            echo "  --help       Show this help message"
            echo ""
            echo "Environment Variables:"
            echo "  SERVER       Target server (default: 138.68.245.159)"
            echo "  SSH_USER     SSH user (default: root)"
            echo "  DB_NAME      Database name (default: trad)"
            exit 0
            ;;
    esac
done

# Functions
log_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

log_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

log_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Check if schema file exists
if [ ! -f "$SCHEMA_FILE" ]; then
    log_error "Schema file not found: $SCHEMA_FILE"
    exit 1
fi

log_info "TradePulse IQ Schema Sync"
log_info "========================="
log_info "Server: $SERVER"
log_info "Database: $DB_NAME"
log_info "Schema File: $SCHEMA_FILE"
echo ""

# Step 1: Get current remote schema
log_info "Step 1/6: Fetching current remote schema..."
ssh $SSH_USER@$SERVER "sudo -u $DB_USER pg_dump -d $DB_NAME --schema-only" > /tmp/remote_schema.sql 2>/dev/null || {
    log_error "Failed to fetch remote schema"
    exit 1
}
log_success "Remote schema fetched"

# Step 2: Compare schemas
log_info "Step 2/6: Comparing local and remote schemas..."

# Extract table definitions for comparison
LOCAL_TABLES=$(grep -E "^CREATE TABLE" $SCHEMA_FILE | awk '{print $3}' | sort)
REMOTE_TABLES=$(grep -E "^CREATE TABLE" /tmp/remote_schema.sql | awk '{print $3}' | sort)

# Show differences
TABLES_ONLY_LOCAL=$(comm -23 <(echo "$LOCAL_TABLES") <(echo "$REMOTE_TABLES"))
TABLES_ONLY_REMOTE=$(comm -13 <(echo "$LOCAL_TABLES") <(echo "$REMOTE_TABLES"))
TABLES_IN_BOTH=$(comm -12 <(echo "$LOCAL_TABLES") <(echo "$REMOTE_TABLES"))

if [ -n "$TABLES_ONLY_LOCAL" ]; then
    log_warning "Tables in local schema but not in remote:"
    echo "$TABLES_ONLY_LOCAL" | sed 's/^/  - /'
fi

if [ -n "$TABLES_ONLY_REMOTE" ]; then
    log_warning "Tables in remote database but not in local schema:"
    echo "$TABLES_ONLY_REMOTE" | sed 's/^/  - /'
fi

log_info "Tables in both: $(echo "$TABLES_IN_BOTH" | wc -l)"
echo ""

# Step 3: Create backup
if [ "$DRY_RUN" = false ]; then
    log_info "Step 3/6: Creating database backup..."
    
    TIMESTAMP=$(date +%Y%m%d_%H%M%S)
    BACKUP_FILE="trad_backup_${TIMESTAMP}.sql"
    
    ssh $SSH_USER@$SERVER "mkdir -p $BACKUP_DIR && sudo -u $DB_USER pg_dump $DB_NAME > $BACKUP_DIR/$BACKUP_FILE" || {
        log_error "Failed to create backup"
        exit 1
    }
    
    log_success "Backup created: $BACKUP_DIR/$BACKUP_FILE"
else
    log_info "Step 3/6: [DRY RUN] Would create backup"
fi

# Step 4: Get schema differences
log_info "Step 4/6: Analyzing schema changes..."

# Count tables, indexes, views
LOCAL_TABLE_COUNT=$(echo "$LOCAL_TABLES" | wc -l)
REMOTE_TABLE_COUNT=$(echo "$REMOTE_TABLES" | wc -l)
LOCAL_INDEX_COUNT=$(grep -c "CREATE INDEX" $SCHEMA_FILE || echo 0)
REMOTE_INDEX_COUNT=$(grep -c "CREATE INDEX" /tmp/remote_schema.sql || echo 0)

echo "  Tables:  Local=$LOCAL_TABLE_COUNT  Remote=$REMOTE_TABLE_COUNT"
echo "  Indexes: Local=$LOCAL_INDEX_COUNT  Remote=$REMOTE_INDEX_COUNT"
echo ""

# Step 5: Confirmation
if [ "$FORCE" = false ] && [ "$DRY_RUN" = false ]; then
    log_warning "This will apply the local schema to the remote database."
    log_warning "All existing data will be preserved, but structure changes will be applied."
    echo ""
    read -p "Do you want to continue? (yes/no): " -r
    echo ""
    if [[ ! $REPLY =~ ^[Yy]es$ ]]; then
        log_info "Sync cancelled by user"
        exit 0
    fi
fi

# Step 6: Apply schema
if [ "$DRY_RUN" = false ]; then
    log_info "Step 5/6: Uploading schema file..."
    scp $SCHEMA_FILE $SSH_USER@$SERVER:/tmp/schema.sql || {
        log_error "Failed to upload schema file"
        exit 1
    }
    
    log_info "Step 6/6: Applying schema to remote database..."
    ssh $SSH_USER@$SERVER "sudo -u $DB_USER psql -d $DB_NAME -f /tmp/schema.sql" 2>&1 | tee /tmp/schema_apply.log
    
    # Check for errors in application
    if grep -i "ERROR" /tmp/schema_apply.log > /dev/null; then
        log_error "Errors occurred during schema application. Check /tmp/schema_apply.log"
        log_warning "Database backup available at: $BACKUP_DIR/$BACKUP_FILE"
        exit 1
    fi
    
    log_success "Schema applied successfully!"
else
    log_info "Step 5/6: [DRY RUN] Would upload $SCHEMA_FILE"
    log_info "Step 6/6: [DRY RUN] Would apply schema to database"
fi

echo ""
log_success "Schema sync completed!"

# Step 7: Verify schema
log_info "Verifying schema..."
ssh $SSH_USER@$SERVER "sudo -u $DB_USER psql -d $DB_NAME -c '\dt'" | head -20

echo ""
log_info "Summary:"
log_info "  - Backup location: $BACKUP_DIR/$BACKUP_FILE"
log_info "  - Schema file: $SCHEMA_FILE"
log_info "  - Database: $DB_NAME on $SERVER"
echo ""

if [ "$DRY_RUN" = true ]; then
    log_info "This was a DRY RUN. No changes were made."
    log_info "Run without --dry-run to apply changes."
fi
