@echo off
chcp 65001 >nul
setlocal

set "APP_DIR=%~dp0dashboard-next"

echo.
echo ========================================
echo  Deploy Showei Sales Dashboard to Vercel
echo ========================================
echo.

if not exist "%APP_DIR%\package.json" (
  echo dashboard-next folder was not found.
  echo Path: %APP_DIR%
  pause
  exit /b 1
)

where vercel.cmd >nul 2>nul
if errorlevel 1 (
  echo Vercel CLI was not found.
  echo Installing Vercel CLI globally...
  call npm.cmd install -g vercel
  if errorlevel 1 (
    echo Failed to install Vercel CLI.
    pause
    exit /b 1
  )
)

cd /d "%APP_DIR%"

call npm.cmd run build
if errorlevel 1 (
  echo Build failed. Fix the error and try again.
  pause
  exit /b 1
)

call vercel.cmd whoami >nul 2>nul
if errorlevel 1 (
  echo Vercel login is required.
  call vercel.cmd login
  if errorlevel 1 (
    echo Vercel login failed.
    pause
    exit /b 1
  )
)

echo.
echo Deploying to production...
echo If Vercel asks setup questions, use:
echo - Set up and deploy: Y
echo - Scope: your account
echo - Link to existing project: N
echo - Project name: showei-ai-sale
echo - Directory: ./
echo.

call vercel.cmd --prod

echo.
echo Deployment command finished.
pause
