param(
  [string]$AppName = "metadata-harmonisation-tool",
  [string]$OllamaBaseUrl = $env:OLLAMA_BASE_URL
)

function Info($msg){ Write-Host "[INFO] $msg" }
function Warn($msg){ Write-Host "[WARN] $msg" -ForegroundColor Yellow }
function Fail($msg){ Write-Host "[ERROR] $msg" -ForegroundColor Red; exit 1 }

# 1) Verify Docker daemon
try {
  docker info | Out-Null
} catch {
  Fail "Docker does not appear to be running. Start Docker Desktop and retry."
}
Info "Docker is running: $(docker --version)"

# 2) Determine Ollama endpoint
if (-not $OllamaBaseUrl -or $OllamaBaseUrl -eq '') {
  $OllamaBaseUrl = "http://localhost:11434"
}
Info "Using OLLAMA_BASE_URL=$OllamaBaseUrl"

# 3) Check Ollama reachability
try {
  $resp = Invoke-WebRequest -Uri "$OllamaBaseUrl/api/tags" -UseBasicParsing -TimeoutSec 5
  if ($resp.StatusCode -eq 200) {
    Info "Ollama reachable (HTTP 200)."
  } else {
    Warn "Ollama responded with HTTP $($resp.StatusCode)."
  }
} catch {
  Warn "Ollama not reachable at $OllamaBaseUrl. If running in Docker, try http://host.docker.internal:11434"
}

# 4) Check app container health (if running)
$container = docker ps --filter "name=$AppName" --format '{{.ID}}'
if ($container) {
  Info "App container detected: $AppName ($container)"
  try {
    $appHealth = Invoke-WebRequest -Uri "http://localhost:8501/_stcore/health" -UseBasicParsing -TimeoutSec 5
    if ($appHealth.StatusCode -eq 200) {
      Info "App health endpoint reachable on http://localhost:8501/_stcore/health"
    } else {
      Warn "App health endpoint returned HTTP $($appHealth.StatusCode). Showing container Health object:"
      docker inspect -f '{{json .State.Health}}' $container | ConvertFrom-Json | Format-List *
    }
  } catch {
    Warn "App health endpoint not reachable on host. Showing container Health object:"
    docker inspect -f '{{json .State.Health}}' $container | ConvertFrom-Json | Format-List *
  }
} else {
  Warn "No running container named '$AppName' found. If you expect it running, use 'docker ps' to verify."
}

Info "Verification complete."
