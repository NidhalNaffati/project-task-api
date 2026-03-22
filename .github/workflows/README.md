# GitHub Actions CI/CD (GCP / Cloud Run)

This repo includes two workflows:

- `ci.yml`: runs tests (`pytest`) on PRs and pushes to `main`.
- `deploy.yml`: on pushes to `main` (and manual dispatch) builds & pushes the Docker image to Artifact Registry, then deploys to Cloud Run by running `./deploy-app.sh`.

## 1) GitHub configuration

Create **GitHub Environments** (`staging`, `production`) and set variables/secrets per environment.

### Environment variables (Settings → Environments → *env* → Variables)

| Name | Example | Notes |
|---|---|---|
| `GCP_PROJECT_ID` | `my-project` | GCP project id |
| `GCP_REGION` | `europe-west1` | Must match your Cloud Run/AR region |
| `AR_REPO` | `project-task-api` | Artifact Registry repo name |
| `CLOUD_RUN_SERVICE` | `project-task-api` | Cloud Run service name |
| `DB_INSTANCE_NAME` | `projectdb-instance` | Cloud SQL instance name |
| `DB_NAME` | `projectdb` | Database created by `deploy-db.sh` |
| `DB_USER` | `appuser` | DB user created by `deploy-db.sh` |
| `CLOUD_SQL_CONNECTION_NAME` | `project:region:instance` | Output of `deploy-db.sh` (`connectionName`) |

### Environment secrets (Settings → Environments → *env* → Secrets)

| Name | Notes |
|---|---|
| `DB_PASSWORD` | Must match the password for `DB_USER` |
| `GCP_WORKLOAD_IDENTITY_PROVIDER` | Workload identity provider resource name |
| `GCP_SERVICE_ACCOUNT_EMAIL` | Service account used for deployments |

## 2) GCP setup (Workload Identity Federation)

The deploy workflow uses OIDC (recommended) via `google-github-actions/auth@v2`.

High-level steps (run once):

1. Create a deployer service account, e.g. `github-deployer`.
2. Create a Workload Identity Pool + Provider for GitHub.
3. Grant the provider permission to impersonate the service account.
4. Grant the service account the IAM roles required to run `deploy-app.sh`.

Google provides a guided setup:

- https://github.com/google-github-actions/auth#setup

### Minimal IAM roles (typical for this repo’s scripts)

`deploy-app.sh` can:

- enable APIs
- create Artifact Registry repos
- push images
- patch a Cloud SQL instance
- deploy to Cloud Run

Depending on what already exists (APIs enabled, AR repo created), you can reduce permissions.

Common roles to grant to the deployer **service account**:

- `roles/run.admin`
- `roles/artifactregistry.admin` (or `writer` if repo already exists)
- `roles/cloudsql.admin` (script patches authorized networks)
- `roles/serviceusage.serviceUsageAdmin` (only if workflow enables APIs)
- `roles/iam.serviceAccountUser` on the Cloud Run runtime service account (usually the default compute SA)

## 3) Notes / security

- `deploy-app.sh` currently sets Cloud SQL authorized networks to `0.0.0.0/0` to allow Cloud Run’s dynamic egress IPs. Consider migrating to Cloud SQL connectors/private IP for production.
- `deploy-db.sh` stores DB secrets in Secret Manager, but `deploy-app.sh` expects `DB_PASSWORD` as an environment variable. You can keep `DB_PASSWORD` in GitHub Secrets, or extend `deploy-app.sh` to fetch it from Secret Manager at deploy time.

