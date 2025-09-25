@echo off
echo Starting Git operations...

git add .
git commit -m "new" --allow-empty
git pull origin master --allow-unrelated-histories --no-edit
git push origin master

echo Done!
pause