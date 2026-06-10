@echo off
chcp 65001 >nul
setlocal

set "APP_DIR=%~dp0dashboard-next"
set "APP_URL=http://localhost:18732"

echo.
echo ========================================
echo  Starting Showei Sales Dashboard
echo ========================================
echo.

if not exist "%APP_DIR%\package.json" (
  echo dashboard-next folder was not found.
  echo Path: %APP_DIR%
  echo.
  pause
  exit /b 1
)

where npm.cmd >nul 2>nul
if errorlevel 1 (
  echo npm was not found. Please install Node.js and try again.
  echo.
  pause
  exit /b 1
)

cd /d "%APP_DIR%"

if not exist "node_modules" (
  echo Installing packages for the first run...
  call npm.cmd install
  if errorlevel 1 (
    echo.
    echo npm install failed.
    pause
    exit /b 1
  )
)

if exist ".next" (
  echo Clearing old Next.js cache...
  rmdir /s /q ".next"
)

echo.
echo URL: %APP_URL%
echo Keep this window open while using the dashboard.
echo Press Ctrl + C to stop the server.
echo.

start "" "%APP_URL%"
call npm.cmd run dev -- --port 18732

echo.
echo Dashboard stopped.
pause
