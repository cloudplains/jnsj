#!/usr/bin/env python3
"""
自动同步 IPTV 文件到 GitHub 仓库 - 修复版本
"""

import requests
import os
import json
import hashlib
import subprocess
import shutil
from datetime import datetime
import argparse

# 配置参数
SOURCE_URL = "https://raw.githubusercontent.com/vbskycn/iptv/refs/heads/master/tv/iptv4.txt"
LOCAL_FILE_PATH = "iptv4.txt"
REPO_DIR = "./jnsj_repo"
GITHUB_REPO = "cloudplains/jnsj"
GITHUB_USERNAME = "github-actions[bot]"
GITHUB_EMAIL = "github-actions[bot]@users.noreply.github.com"
COMMIT_MSG = "自动更新 IPTV 文件 - {}"

def get_file_hash(content):
    """计算文件内容的哈希值"""
    return hashlib.md5(content.encode('utf-8')).hexdigest()

def download_iptv_file():
    """下载 IPTV 文件"""
    try:
        response = requests.get(SOURCE_URL, timeout=30)
        response.raise_for_status()
        return response.text
    except requests.RequestException as e:
        print(f"下载文件失败: {e}")
        return None

def run_command(cmd, cwd=None):
    """运行 shell 命令"""
    try:
        result = subprocess.run(cmd, shell=True, capture_output=True, text=True, cwd=cwd)
        if result.returncode != 0:
            print(f"命令执行失败: {cmd}")
            print(f"错误输出: {result.stderr}")
            return False, result.stderr
        return True, result.stdout
    except Exception as e:
        print(f"执行命令时发生异常: {e}")
        return False, str(e)

def setup_git_repo(github_token):
    """设置 Git 仓库"""
    # 如果目录已存在，先删除
    if os.path.exists(REPO_DIR):
        shutil.rmtree(REPO_DIR)
    
    os.makedirs(REPO_DIR)
    
    # 克隆仓库
    repo_url = f"https://{github_token}@github.com/{GITHUB_REPO}.git"
    success, output = run_command(f"git clone {repo_url} .", cwd=REPO_DIR)
    if not success:
        return False
    
    # 配置 Git 用户信息
    run_command(f"git config user.name '{GITHUB_USERNAME}'", cwd=REPO_DIR)
    run_command(f"git config user.email '{GITHUB_EMAIL}'", cwd=REPO_DIR)
    
    return True

def sync_file_to_github(github_token):
    """同步文件到 GitHub"""
    # 下载最新文件
    new_content = download_iptv_file()
    if new_content is None:
        return False
    
    # 设置 Git 仓库
    if not setup_git_repo(github_token):
        return False
    
    # 检查文件是否已存在
    local_file = os.path.join(REPO_DIR, LOCAL_FILE_PATH)
    file_exists = os.path.exists(local_file)
    
    # 检查内容是否有变化
    content_changed = True
    if file_exists:
        with open(local_file, 'r', encoding='utf-8') as f:
            old_content = f.read()
        
        old_hash = get_file_hash(old_content)
        new_hash = get_file_hash(new_content)
        content_changed = (old_hash != new_hash)
    
    # 如果没有变化，则不需要提交
    if not content_changed:
        print("文件内容无变化，无需更新")
        return True
    
    # 写入新内容
    with open(local_file, 'w', encoding='utf-8') as f:
        f.write(new_content)
    
    # 提交更改
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    commit_message = COMMIT_MSG.format(timestamp)
    
    # 添加文件
    success, output = run_command(f"git add {LOCAL_FILE_PATH}", cwd=REPO_DIR)
    if not success:
        return False
    
    # 提交更改
    success, output = run_command(f'git commit -m "{commit_message}"', cwd=REPO_DIR)
    if not success and "nothing to commit" not in output:
        return False
    
    # 推送更改
    success, output = run_command("git push origin main", cwd=REPO_DIR)
    if not success:
        return False
    
    print("已成功推送更新到 GitHub")
    return True

def main():
    parser = argparse.ArgumentParser(description='同步 IPTV 文件到 GitHub 仓库')
    parser.add_argument('--github-token', required=True, help='GitHub 访问令牌')
    
    args = parser.parse_args()
    
    success = sync_file_to_github(args.github_token)
    if not success:
        print("同步失败")
        exit(1)
    else:
        print("同步成功")

if __name__ == "__main__":
    main()