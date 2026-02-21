# TruthChain Local Database Setup (PowerShell)
# Run this script to set up PostgreSQL locally

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "TruthChain Local PostgreSQL Setup" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

# Get PostgreSQL password
$env:PGPASSWORD = Read-Host "Enter PostgreSQL password for user 'postgres'" -AsSecureString
$env:PGPASSWORD = [System.Runtime.InteropServices.Marshal]::PtrToStringAuto([System.Runtime.InteropServices.Marshal]::SecureStringToBSTR($env:PGPASSWORD))

# Create database
Write-Host "[1/3] Creating truthchain database..." -ForegroundColor Yellow
$result = psql -U postgres -c "CREATE DATABASE truthchain;" 2>&1
if ($LASTEXITCODE -eq 0) {
    Write-Host "✓ Database created successfully" -ForegroundColor Green
} else {
    if ($result -match "already exists") {
        Write-Host "! Database already exists (OK)" -ForegroundColor Yellow
    } else {
        Write-Host "✗ Error: $result" -ForegroundColor Red
        exit 1
    }
}

# Create tables
Write-Host ""
Write-Host "[2/3] Creating database tables..." -ForegroundColor Yellow
Set-Location backend
$result = Get-Content create_tables.sql | psql -U postgres -d truthchain 2>&1
Set-Location ..
if ($LASTEXITCODE -eq 0) {
    Write-Host "✓ Tables created successfully" -ForegroundColor Green
} else {
    Write-Host "! Check output: $result" -ForegroundColor Yellow
}

# Verify tables
Write-Host ""
Write-Host "[3/3] Verifying tables..." -ForegroundColor Yellow
psql -U postgres -d truthchain -c "\dt"

Write-Host ""
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "PostgreSQL Setup Complete!" -ForegroundColor Green
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "Database: truthchain" -ForegroundColor White
Write-Host "Host: localhost" -ForegroundColor White
Write-Host "Port: 5432" -ForegroundColor White
Write-Host "User: postgres" -ForegroundColor White
Write-Host ""

# Check for Redis
Write-Host "Checking for Redis..." -ForegroundColor Yellow
$redisInstalled = Get-Command redis-server -ErrorAction SilentlyContinue
if ($redisInstalled) {
    Write-Host "✓ Redis is installed" -ForegroundColor Green
} else {
    Write-Host "! Redis not found" -ForegroundColor Yellow
    Write-Host ""
    Write-Host "Install Redis for Windows:" -ForegroundColor Cyan
    Write-Host "  Option 1 (Memurai - Free): https://www.memurai.com/get-memurai" -ForegroundColor White
    Write-Host "  Option 2 (Chocolatey): choco install memurai-developer" -ForegroundColor White
    Write-Host "  Option 3 (WSL): wsl --install (then install redis)" -ForegroundColor White
}

Write-Host ""
