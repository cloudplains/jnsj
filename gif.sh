#!/bin/bash
echo "🎯 开始执行Git操作..."
echo ""

# 添加所有更改
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

# 拉取远程更新
echo "⬇️  拉取远程更改..."
git pull origin main
echo "✅ 拉取完成"
echo ""

# 推送到远程
echo "⬆️  推送到远程仓库..."
git push origin main
echo "✅ 推送完成"
echo ""

echo "🎉 所有操作已完成！"
