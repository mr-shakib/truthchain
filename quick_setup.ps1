# Quick Local Setup - TruthChain
# This script sets up PostgreSQL locally

Write-Host "`n========================================" -ForegroundColor Cyan
Write-Host "TruthChain Local PostgreSQL Setup" -ForegroundColor Cyan
Write-Host "========================================`n" -ForegroundColor Cyan

# Get password
$password = Read-Host "Enter PostgreSQL 'postgres' user password"
$env:PGPASSWORD = $password

# Create database
Write-Host "`n[1/3] Creating truthchain database..." -ForegroundColor Yellow
psql -U postgres -c "CREATE DATABASE truthchain;" 2>&1 | Out-Null
if ($LASTEXITCODE -eq 0 -or $LASTEXITCODE -eq 1) {
    Write-Host "✓ Database ready" -ForegroundColor Green
}

# Create tables  
Write-Host "`n[2/3] Creating tables..." -ForegroundColor Yellow
Get-Content backend\create_tables.sql | psql -U postgres -d truthchain
if ($LASTEXITCODE -eq 0) {
    Write-Host "✓ Tables created" -ForegroundColor Green
}

# Verify
Write-Host "`n[3/3] Verifying..." -ForegroundColor Yellow
psql -U postgres -d truthchain -c "\dt"

Write-Host "`n========================================" -ForegroundColor Green
Write-Host "Setup Complete!" -ForegroundColor Green  
Write-Host "========================================`n" -ForegroundColor Green

Write-Host "Database: truthchain" -ForegroundColor White
Write-Host "Host: localhost:5432" -ForegroundColor White
Write-Host "User: postgres`n" -ForegroundColor White

# Remove password from environment
Remove-Item Env:\PGPASSWORD
