#!/bin/bash

# 设置错误时退出
set -e

echo "🎯 开始执行Git操作..."
echo ""

# 检查Git身份配置
if [[ -z "$(git config user.email)" || -z "$(git config user.name)" ]]; then
    echo "❌ Git身份未配置！"
    echo ""
    echo "请先配置Git身份信息："
    echo "git config --global user.email \"your-email@example.com\""
    echo "git config --global user.name \"Your Name\""
    echo ""
    echo "或为当前仓库单独配置："
    echo "git config user.email \"your-email@example.com\""
    echo "git config user.name \"Your Name\""
    exit 1
fi

# 检查是否有需要提交的更改
if git diff --quiet && git diff --cached --quiet; then
    echo "📭 没有检测到需要提交的更改"
    skip_commit=true
else
    skip_commit=false
    echo "📦 添加更改到暂存区..."
    git add .
    echo "✅ 添加完成"
    echo ""

    # 提交更改（带时间戳）
    commit_msg="Auto commit at $(date +'%Y-%m-%d %H:%M:%S')"
    echo "📝 提交更改：$commit_msg"
    git commit -m "$commit_msg"
    echo "✅ 提交完成"
    echo ""
fi

# 拉取远程更新（使用rebase避免额外合并提交）
echo "⬇️  拉取远程更改..."
if git pull --rebase origin main; then
    echo "✅ 拉取完成"
    echo ""
else
    echo "❌ 拉取失败，可能存在冲突"
    echo ""
    echo "请手动解决冲突后："
    echo "1. 检查冲突文件：git status"
    echo "2. 解决冲突后：git add ."
    echo "3. 继续rebase：git rebase --continue"
    echo "4. 或取消rebase：git rebase --abort"
    exit 1
fi

# 推送到远程
echo "⬆️  推送到远程仓库..."
if git push origin main; then
    echo "✅ 推送完成"
    echo ""
else
    echo "❌ 推送失败"
    echo ""
    echo "可能的原因："
    echo "1. 没有网络连接"
    echo "2. 权限不足"
    echo "3. 远程仓库不存在"
    exit 1
fi

if [ "$skip_commit" = true ]; then
    echo "📤 已同步远程更改（无本地提交）"
else
    echo "🎉 所有操作已完成！"
fi