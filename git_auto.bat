@echo off
echo Starting Git operations...

git add .
git commit -m "new" --allow-empty
git pull origin main --allow-unrelated-histories --no-edit
git push origin main

echo Done!
pause