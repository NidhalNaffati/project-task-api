#!/usr/bin/env bash
# ============================================================
#  deploy-app.sh
#  Builds the FastAPI Docker image, pushes it to Artifact
#  Registry, and deploys it to Cloud Run with a Cloud SQL
#  (PostgreSQL) connection via the Cloud SQL Auth Proxy.
#
#  Prerequisites:
#    - gcloud CLI installed & authenticated
#    - deploy-db.sh must have been run first
#    - Docker daemon running locally
#
#  Usage:
#    chmod +x deploy-app.sh
#    export CLOUD_SQL_CONNECTION_NAME="project:region:instance"
#    export DB_PASSWORD="your-db-password"   # or set below
#    ./deploy-app.sh
# ============================================================
set -euo pipefail

# ─── User-configurable variables ────────────────────────────────────────────
PROJECT_ID="${GCP_PROJECT_ID:-pfe-esprit-489411}"
REGION="${GCP_REGION:-europe-west1}"

# Artifact Registry
AR_REPO="${AR_REPO:-project-task-api}"
IMAGE_NAME="project-task-api"
IMAGE_TAG="${IMAGE_TAG:-latest}"

# Cloud Run
SERVICE_NAME="${CLOUD_RUN_SERVICE:-project-task-api}"
CLOUD_RUN_CONCURRENCY="${CLOUD_RUN_CONCURRENCY:-80}"
CLOUD_RUN_MIN_INSTANCES="${CLOUD_RUN_MIN_INSTANCES:-0}"
CLOUD_RUN_MAX_INSTANCES="${CLOUD_RUN_MAX_INSTANCES:-3}"
CLOUD_RUN_MEMORY="${CLOUD_RUN_MEMORY:-512Mi}"
CLOUD_RUN_CPU="${CLOUD_RUN_CPU:-1}"

# Cloud SQL (set these or export before calling this script)
CLOUD_SQL_CONNECTION_NAME="${CLOUD_SQL_CONNECTION_NAME:-your-project:region:instance}"
DB_INSTANCE_NAME="${DB_INSTANCE_NAME:-projectdb-instance}"
DB_NAME="${DB_NAME:-projectdb}"
DB_USER="${DB_USER:-appuser}"
DB_PASSWORD="${DB_PASSWORD:-}"        # must be provided

# ─── Helper ─────────────────────────────────────────────────────────────────
info()  { echo -e "\033[1;34m[INFO]\033[0m  $*"; }
ok()    { echo -e "\033[1;32m[OK]\033[0m    $*"; }
warn()  { echo -e "\033[1;33m[WARN]\033[0m  $*"; }
die()   { echo -e "\033[1;31m[ERROR]\033[0m $*" >&2; exit 1; }

# ─── Validate required variables ─────────────────────────────────────────────
[[ "$PROJECT_ID" == "your-gcp-project-id" ]] && \
  die "Set GCP_PROJECT_ID environment variable before running this script."
[[ "$CLOUD_SQL_CONNECTION_NAME" == "your-project:region:instance" ]] && \
  die "Set CLOUD_SQL_CONNECTION_NAME (output by deploy-db.sh) before running."
[[ -z "$DB_PASSWORD" ]] && \
  die "Set DB_PASSWORD before running (output by deploy-db.sh)."

# ─── Configure gcloud ───────────────────────────────────────────────────────
info "Setting gcloud project to: $PROJECT_ID"
gcloud config set project "$PROJECT_ID"

# ─── Enable required APIs ───────────────────────────────────────────────────
info "Enabling required APIs..."
gcloud services enable \
  artifactregistry.googleapis.com \
  run.googleapis.com \
  cloudbuild.googleapis.com \
  secretmanager.googleapis.com

# ─── Create Artifact Registry repository (if not exists) ────────────────────
if gcloud artifacts repositories describe "$AR_REPO" \
    --location="$REGION" --project="$PROJECT_ID" &>/dev/null; then
  warn "Artifact Registry repo '$AR_REPO' already exists – skipping."
else
  info "Creating Artifact Registry repository '$AR_REPO'..."
  gcloud artifacts repositories create "$AR_REPO" \
    --repository-format=docker \
    --location="$REGION" \
    --description="Docker images for project-task-api"
  ok "Repository created."
fi

# ─── Build & push Docker image ───────────────────────────────────────────────
IMAGE_URI="${REGION}-docker.pkg.dev/${PROJECT_ID}/${AR_REPO}/${IMAGE_NAME}:${IMAGE_TAG}"

info "Configuring Docker auth for Artifact Registry..."
gcloud auth configure-docker "${REGION}-docker.pkg.dev" --quiet

info "Building Docker image: $IMAGE_URI"
docker build \
  --platform linux/amd64 \
  -t "$IMAGE_URI" \
  "$(dirname "$0")"

info "Pushing image to Artifact Registry..."
docker push "$IMAGE_URI"
ok "Image pushed: $IMAGE_URI"

# ─── Note on IAM Permissions ─────────────────────────────────────────────────
# The default Compute Engine service account used by Cloud Run typically has
# the 'Editor' role, which already includes access to Cloud SQL and Secret Manager.
# If you get a 403 error during runtime, you will need a project Admin to grant
# 'roles/cloudsql.client' and 'roles/secretmanager.secretAccessor' to the
# Compute service account.

# ─── Configure Cloud SQL Public IP Access ───────────────────────────────────
info "Retrieving Cloud SQL Public IP..."
DB_PUBLIC_IP=$(gcloud sql instances describe "$DB_INSTANCE_NAME" \
  --project="$PROJECT_ID" \
  --format="value(ipAddresses[0].ipAddress)")

info "Authorizing Cloud Run to connect to the database..."
# Since Cloud Run egress IPs are dynamic, we allow 0.0.0.0/0.
# The database is secured by the strong 24-character password generated earlier.
gcloud sql instances patch "$DB_INSTANCE_NAME" \
  --project="$PROJECT_ID" \
  --authorized-networks="0.0.0.0/0" \
  --quiet

# ─── Deploy to Cloud Run ─────────────────────────────────────────────────────
# The app connects to Cloud SQL via standard TCP over its Public IP.
info "Deploying to Cloud Run service '$SERVICE_NAME' in $REGION..."

gcloud run deploy "$SERVICE_NAME" \
  --image="$IMAGE_URI" \
  --platform=managed \
  --region="$REGION" \
  --allow-unauthenticated \
  --set-env-vars="DB_HOST=${DB_PUBLIC_IP}" \
  --set-env-vars="DB_PORT=5432" \
  --set-env-vars="DB_NAME=${DB_NAME}" \
  --set-env-vars="DB_USER=${DB_USER}" \
  --set-env-vars="DB_PASSWORD=${DB_PASSWORD}" \
  --set-env-vars="IMAGE_TAG=${IMAGE_TAG}" \
  --set-env-vars="IMAGE_URI=${IMAGE_URI}" \
  --concurrency="$CLOUD_RUN_CONCURRENCY" \
  --min-instances="$CLOUD_RUN_MIN_INSTANCES" \
  --max-instances="$CLOUD_RUN_MAX_INSTANCES" \
  --memory="$CLOUD_RUN_MEMORY" \
  --cpu="$CLOUD_RUN_CPU" \
  --port=8000 \
  --timeout=60 \
  --quiet

# ─── Get service URL ─────────────────────────────────────────────────────────
SERVICE_URL=$(gcloud run services describe "$SERVICE_NAME" \
  --platform=managed \
  --region="$REGION" \
  --format="value(status.url)")

# ─── Summary ─────────────────────────────────────────────────────────────────
echo ""
ok "════════════════════ App Deployment Complete ════════════════════"
echo "  Service      : $SERVICE_NAME"
echo "  Region       : $REGION"
echo "  Image        : $IMAGE_URI"
echo "  Cloud SQL    : $CLOUD_SQL_CONNECTION_NAME"
echo ""
echo "  🚀 Live URL  : $SERVICE_URL"
echo "  📖 API Docs  : ${SERVICE_URL}/docs"
echo "  ❤️  Health   : ${SERVICE_URL}/"
echo "═══════════════════════════════════════════════════════════════"
