@echo off
REM TruthChain Local Database Setup Script

echo ========================================
echo TruthChain Local PostgreSQL Setup
echo ========================================
echo.

REM Create database
echo [1/3] Creating truthchain database...
psql -U postgres -c "CREATE DATABASE truthchain;" 2>nul
if %errorlevel% equ 0 (
    echo ✓ Database created successfully
) else (
    echo ! Database may already exist or check password
)

REM Create tables
echo.
echo [2/3] Creating database tables...
psql -U postgres -d truthchain -f backend\create_tables.sql
if %errorlevel% equ 0 (
    echo ✓ Tables created successfully
) else (
    echo ! Error creating tables
)

REM Verify tables
echo.
echo [3/3] Verifying tables...
psql -U postgres -d truthchain -c "\dt"

echo.
echo ========================================
echo Setup Complete!
echo ========================================
echo.
echo Database: truthchain
echo Host: localhost
echo Port: 5432
echo User: postgres
echo.
echo Next: Install Redis locally
echo.
pause
