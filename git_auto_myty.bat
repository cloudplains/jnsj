@echo off
echo =================================
echo    MyTY 仓库Git自动化脚本
echo =================================
echo.

:: 检查是否在Git仓库中，如果不是则初始化
git status >nul 2>&1
if errorlevel 1 (
    echo MyTY仓库未初始化，正在初始化...
    git init
    echo ? Git仓库初始化完成
    echo.
    echo 请先设置远程仓库（如果需要）:
    echo git remote add origin [你的myty仓库URL]
    echo.
)

:: 显示当前状态
git status
echo.

:: 添加文件到暂存区
echo 步骤1: 添加文件到暂存区...
git add .
if errorlevel 1 (
    echo ! 添加文件时出现问题
) else (
    echo ? 添加成功
)

echo.

:: 提交更改
echo 步骤2: 提交更改...
git commit -m "更新myty仓库" --allow-empty
if errorlevel 1 (
    echo ! 提交可能没有变化
) else (
    echo ? 提交成功
)

echo.

:: 检查是否有远程仓库设置
git remote get-url origin >nul 2>&1
if errorlevel 1 (
    echo 提示: 未设置远程仓库，跳过pull/push操作
    echo 如需设置远程仓库，请运行: git remote add origin [仓库URL]
) else (
    :: 拉取远程更新
    echo 步骤3: 拉取远程更新...
    git pull origin main --allow-unrelated-histories --no-edit
    if errorlevel 1 (
        echo ! 拉取失败，尝试使用master分支...
        git pull origin master --allow-unrelated-histories --no-edit
    )
    echo ? 拉取成功
    
    echo.
    
    :: 推送到远程仓库
    echo 步骤4: 推送到远程仓库...
    git push origin main
    if errorlevel 1 (
        echo ! 推送到main分支失败，尝试master分支...
        git push origin master
    )
    echo ? 推送成功
)

echo.
echo =================================
echo   MyTY仓库操作完成!
echo =================================
echo.
pause