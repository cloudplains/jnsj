@echo off
echo Starting Git operations for myty repository...

git add .
git commit -m "update" --allow-empty
git pull origin main --allow-unrelated-histories --no-edit
git push origin main

echo myty repository update completed!
pause