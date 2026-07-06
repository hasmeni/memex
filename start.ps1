# ironyLabs Links — start.ps1
# Usage: .\start.ps1
# Optional env vars: $env:ADMIN_PASSWORD, $env:SECRET_KEY

Write-Host "ironyLabs Links — starting..." -ForegroundColor DarkYellow

# Set defaults if not already set
if (-not $env:ADMIN_PASSWORD) { $env:ADMIN_PASSWORD = "ironyLabs2024!" }
if (-not $env:SECRET_KEY)     { $env:SECRET_KEY = "supersecretkey_change_me" }

docker compose up -d --build

Write-Host ""
Write-Host "Running at http://localhost:8098" -ForegroundColor Green
Write-Host "Admin panel: http://localhost:8098/admin.html" -ForegroundColor Cyan
Write-Host "Default password: $env:ADMIN_PASSWORD" -ForegroundColor DarkGray
