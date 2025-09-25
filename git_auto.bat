@echo off
chcp 65001 >nul
echo ========================================
echo          Git Automation Script
echo ========================================
echo.

:: Check if current directory is a git repository
git status
if errorlevel 1 (
    echo Error: Not a git repository!
    echo Please make sure this bat file is in the root of a git repository
    pause
    exit /b 1
)

echo Step 1: Adding changes...
git add .
if errorlevel 1 (
    echo Error: git add failed!
    pause
    exit /b 1
)
echo ? Add successful

echo.
echo Step 2: Committing changes...
git commit -m "new" --allow-empty
if errorlevel 1 (
    echo ! Commit might have no changes, continuing...
)

echo.
echo Step 3: Pulling from remote...
git pull origin main --no-edit
if errorlevel 1 (
    echo Error: git pull failed!
    pause
    exit /b 1
)
echo ? Pull successful

echo.
echo Step 4: Pushing to remote...
git push origin main
if errorlevel 1 (
    echo Error: git push failed!
    pause
    exit /b 1
)
echo ? Push successful

echo.
echo ========================================
echo          All operations completed!
echo ========================================
echo.
pause