#!/usr/bin/env bash
set -euo pipefail

# Seed the deployed Project & Task API via HTTP (curl).
#
# Usage (public service):
#   ./scripts/seed_remote.sh
#
# Usage (Cloud Run requires auth):
#   TOKEN="$(gcloud auth print-identity-token)" \
#     ./scripts/seed_remote.sh
#
# Override the target service URL (optional):
#   BASE_URL="https://your-service.run.app" ./scripts/seed_remote.sh
#
# Notes:
# - Best-effort idempotent: it tries to reuse existing tasks/projects by
#   matching by title/name. If duplicates already exist server-side, it uses the
#   first match.
# - Requires: curl
# - Optional but recommended: jq (for robust JSON parsing)

# Default target (your deployed Cloud Run service)
: "${BASE_URL:=https://project-task-api-1068943233669.europe-west1.run.app}"

BASE_URL="${BASE_URL%/}"
API="$BASE_URL/api/v1"

AUTH_HEADER=()
if [[ -n "${TOKEN:-}" ]]; then
  AUTH_HEADER=(-H "Authorization: Bearer $TOKEN")
fi

need_cmd() {
  command -v "$1" >/dev/null 2>&1 || {
    echo "Missing required command: $1" >&2
    exit 1
  }
}

need_cmd curl
need_cmd jq

http_get() {
  curl -fsS "${AUTH_HEADER[@]}" "$1"
}

http_post_json() {
  local url="$1"
  local json="$2"
  curl -fsS "${AUTH_HEADER[@]}" -H 'Content-Type: application/json' -d "$json" "$url"
}

# Returns the id of the first element matching .title == $title
find_task_id_by_title() {
  local title="$1"
  http_get "$API/tasks/" | jq -r --arg title "$title" '.[] | select(.title==$title) | .id' | head -n 1
}

find_project_id_by_name() {
  local name="$1"
  http_get "$API/projects/" | jq -r --arg name "$name" '.[] | select(.name==$name) | .id' | head -n 1
}

ensure_task() {
  local title="$1"
  local description="$2"
  local tags_json="$3" # JSON array string, e.g. ["backend","api"]

  local id
  id="$(find_task_id_by_title "$title" || true)"
  if [[ -n "$id" && "$id" != "null" ]]; then
    echo "$id"
    return 0
  fi

  local payload
  payload="$(
    jq -nc --arg title "$title" --arg description "$description" --argjson tags "$tags_json" \
      '{title:$title, description:$description, tags:$tags}'
  )"

  http_post_json "$API/tasks/" "$payload" | jq -r '.id'
}

ensure_project() {
  local name="$1"
  local budget="$2"
  local hours_used="$3"
  local description="$4"

  local id
  id="$(find_project_id_by_name "$name" || true)"
  if [[ -n "$id" && "$id" != "null" ]]; then
    echo "$id"
    return 0
  fi

  local payload
  payload="$(
    jq -nc --arg name "$name" --arg description "$description" --argjson budget "$budget" --argjson hours_used "$hours_used" \
      '{name:$name, budget:$budget, hours_used:$hours_used, description:$description}'
  )"

  http_post_json "$API/projects/" "$payload" | jq -r '.id'
}

assign_task_to_project() {
  local project_id="$1"
  local task_id="$2"

  # 200 = assigned, 409 = already assigned
  local code
  code="$(curl -sS -o /dev/null -w '%{http_code}' "${AUTH_HEADER[@]}" -X POST "$API/projects/$project_id/tasks/$task_id")"
  if [[ "$code" != "200" && "$code" != "409" ]]; then
    echo "Failed to assign task $task_id to project $project_id (HTTP $code)" >&2
    exit 1
  fi
}

# ---- Main ----

echo "Checking service health: $BASE_URL/" >&2
http_get "$BASE_URL/" >/dev/null

# Tasks
TASK_DB_SCHEMA_ID="$(ensure_task "Design database schema" "Draw ER diagram and decide on indexes" '["backend","database"]')"
TASK_REST_API_ID="$(ensure_task "Implement REST API" "Build CRUD endpoints with FastAPI" '["backend","api"]')"
TASK_TESTS_ID="$(ensure_task "Write unit tests" "Cover key scenarios with pytest" '["backend","qa"]')"
TASK_LANDING_ID="$(ensure_task "Build landing page" "Create responsive landing page" '["frontend","ui"]')"
TASK_CICD_ID="$(ensure_task "Set up CI/CD pipeline" "Configure CI to run tests and build images" '["devops","ci-cd"]')"
TASK_GCP_ID="$(ensure_task "Deploy to GCP" "Deploy the service on Cloud Run" '["devops","cloud","gcp"]')"

# Projects
PROJ_WEB_ID="$(ensure_project "Website Redesign" 50000.0 120.5 "Redesign the company public website")"
PROJ_DEVOPS_ID="$(ensure_project "Internal DevOps Tooling" 30000.0 80.0 "Automate CI/CD and infrastructure provisioning")"
PROJ_API_ID="$(ensure_project "API Platform" 75000.0 200.0 "Build a centralised API platform")"

# Assignments
assign_task_to_project "$PROJ_WEB_ID" "$TASK_DB_SCHEMA_ID"
assign_task_to_project "$PROJ_WEB_ID" "$TASK_REST_API_ID"
assign_task_to_project "$PROJ_WEB_ID" "$TASK_LANDING_ID"

assign_task_to_project "$PROJ_DEVOPS_ID" "$TASK_CICD_ID"
assign_task_to_project "$PROJ_DEVOPS_ID" "$TASK_GCP_ID"

assign_task_to_project "$PROJ_API_ID" "$TASK_DB_SCHEMA_ID"
assign_task_to_project "$PROJ_API_ID" "$TASK_REST_API_ID"
assign_task_to_project "$PROJ_API_ID" "$TASK_TESTS_ID"

# Summary
TASKS_COUNT="$(http_get "$API/tasks/" | jq 'length')"
PROJECTS_COUNT="$(http_get "$API/projects/" | jq 'length')"

printf 'Seed complete. Tasks: %s | Projects: %s\n' "$TASKS_COUNT" "$PROJECTS_COUNT"


