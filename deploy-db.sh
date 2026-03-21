#!/usr/bin/env bash
# ============================================================
#  deploy-db.sh
#  Provisions a Cloud SQL (PostgreSQL 16) instance on GCP
#  and creates the application database + user.
#
#  Prerequisites:
#    - gcloud CLI installed & authenticated (gcloud auth login)
#    - Billing enabled on the project
#    - APIs: sqladmin.googleapis.com, servicenetworking.googleapis.com
#
#  Usage:
#    chmod +x deploy-db.sh
#    ./deploy-db.sh
# ============================================================
set -euo pipefail

# ─── User-configurable variables ────────────────────────────────────────────
PROJECT_ID="${GCP_PROJECT_ID:-pfe-esprit-489411}"
REGION="${GCP_REGION:-europe-west1}"

# Cloud SQL instance settings
DB_INSTANCE_NAME="${DB_INSTANCE_NAME:-projectdb-instance}"
DB_VERSION="POSTGRES_16"
DB_TIER="${DB_TIER:-db-f1-micro}"          # cheapest tier – change for prod

# Database & credentials
DB_NAME="${DB_NAME:-projectdb}"
DB_USER="${DB_USER:-appuser}"
DB_PASSWORD="${DB_PASSWORD:-$(openssl rand -base64 24)}"   # auto-generate if not set

# ─── Helper ─────────────────────────────────────────────────────────────────
info()  { echo -e "\033[1;34m[INFO]\033[0m  $*"; }
ok()    { echo -e "\033[1;32m[OK]\033[0m    $*"; }
warn()  { echo -e "\033[1;33m[WARN]\033[0m  $*"; }
die()   { echo -e "\033[1;31m[ERROR]\033[0m $*" >&2; exit 1; }

# ─── Validate ───────────────────────────────────────────────────────────────
[[ "$PROJECT_ID" == "your-gcp-project-id" ]] && \
  die "Set GCP_PROJECT_ID environment variable before running this script."

# ─── Configure gcloud ───────────────────────────────────────────────────────
info "Setting gcloud project to: $PROJECT_ID"
gcloud config set project "$PROJECT_ID"

# ─── Enable required APIs ───────────────────────────────────────────────────
info "Enabling Cloud SQL Admin API..."
gcloud services enable sqladmin.googleapis.com

# ─── Create Cloud SQL instance (if not exists) ──────────────────────────────
if gcloud sql instances describe "$DB_INSTANCE_NAME" --project="$PROJECT_ID" &>/dev/null; then
  warn "Cloud SQL instance '$DB_INSTANCE_NAME' already exists – skipping creation."
else
  info "Creating Cloud SQL instance '$DB_INSTANCE_NAME' ($DB_VERSION) in $REGION..."
  gcloud sql instances create "$DB_INSTANCE_NAME" \
    --database-version="$DB_VERSION" \
    --edition=ENTERPRISE \
    --tier="$DB_TIER" \
    --region="$REGION" \
    --storage-auto-increase \
    --storage-size=10 \
    --backup-start-time="03:00" \
    --availability-type=zonal \
    --assign-ip
  ok "Cloud SQL instance created."
fi

# ─── Create database (if not exists) ────────────────────────────────────────
if gcloud sql databases describe "$DB_NAME" --instance="$DB_INSTANCE_NAME" &>/dev/null; then
  warn "Database '$DB_NAME' already exists – skipping."
else
  info "Creating database '$DB_NAME'..."
  gcloud sql databases create "$DB_NAME" \
    --instance="$DB_INSTANCE_NAME"
  ok "Database '$DB_NAME' created."
fi

# ─── Create DB user (if not exists) ─────────────────────────────────────────
if gcloud sql users list --instance="$DB_INSTANCE_NAME" --format="value(name)" | grep -q "^${DB_USER}$"; then
  warn "User '$DB_USER' already exists – updating password."
  gcloud sql users set-password "$DB_USER" \
    --instance="$DB_INSTANCE_NAME" \
    --password="$DB_PASSWORD"
else
  info "Creating database user '$DB_USER'..."
  gcloud sql users create "$DB_USER" \
    --instance="$DB_INSTANCE_NAME" \
    --password="$DB_PASSWORD"
  ok "User '$DB_USER' created."
fi

# ─── Retrieve connection name ────────────────────────────────────────────────
CONNECTION_NAME=$(gcloud sql instances describe "$DB_INSTANCE_NAME" \
  --format="value(connectionName)")

# ─── Store credentials in Secret Manager ────────────────────────────────────
info "Enabling Secret Manager API..."
gcloud services enable secretmanager.googleapis.com

store_secret() {
  local name="$1" value="$2"
  if gcloud secrets describe "$name" --project="$PROJECT_ID" &>/dev/null; then
    warn "Secret '$name' exists – adding new version."
    echo -n "$value" | gcloud secrets versions add "$name" --data-file=-
  else
    info "Creating secret '$name'..."
    echo -n "$value" | gcloud secrets create "$name" \
      --replication-policy=automatic \
      --data-file=-
  fi
}

store_secret "DB_NAME"     "$DB_NAME"
store_secret "DB_USER"     "$DB_USER"
store_secret "DB_PASSWORD" "$DB_PASSWORD"

# ─── Summary ─────────────────────────────────────────────────────────────────
echo ""
ok "════════════════════ Database Deployment Complete ════════════════════"
echo "  Cloud SQL Instance : $DB_INSTANCE_NAME"
echo "  Region             : $REGION"
echo "  Connection Name    : $CONNECTION_NAME"
echo "  Database           : $DB_NAME"
echo "  User               : $DB_USER"
echo "  Password           : $DB_PASSWORD"
echo ""
echo "  ⚠️  Save the password above – it is also stored in Secret Manager."
echo ""
echo "  Pass these to deploy-app.sh:"
echo "    export CLOUD_SQL_CONNECTION_NAME=\"$CONNECTION_NAME\""
echo "    export DB_PASSWORD=\"$DB_PASSWORD\""
echo "═══════════════════════════════════════════════════════════════════════"
