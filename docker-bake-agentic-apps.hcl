variable "PROJECT_ID" {
  default = "gb-poc-373711"
}

variable "LOCATION" {
  default = "europe-west1"
}

variable "REPO_NAME" {
  default = "internal-images"
}

variable "REGISTRY" {
  default = "${LOCATION}-docker.pkg.dev/${PROJECT_ID}/${REPO_NAME}"
}

# Images are suffixed -copilotkit to avoid clashing with the main
# football-agent-adk repo when pushing to the same Artifact Registry.

group "default" {
  targets = ["adk-agent", "webapp"]
}

target "adk-agent" {
  context    = "."
  dockerfile = "Dockerfile"
  tags = ["${REGISTRY}/football-stats-api-copilotkit:latest"]
  cache-from = ["type=registry,ref=${REGISTRY}/football-stats-api-copilotkit:cache"]
  cache-to = ["type=registry,ref=${REGISTRY}/football-stats-api-copilotkit:cache,mode=max"]
}

target "webapp" {
  context    = "./webapp"
  dockerfile = "Dockerfile"
  tags = ["${REGISTRY}/football-stats-webapp-copilotkit:latest"]
  cache-from = ["type=registry,ref=${REGISTRY}/football-stats-webapp-copilotkit:cache"]
  cache-to = ["type=registry,ref=${REGISTRY}/football-stats-webapp-copilotkit:cache,mode=max"]
}
