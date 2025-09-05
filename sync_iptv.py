#!/usr/bin/env python3
"""
自动同步 IPTV 文件到 GitHub 仓库
"""

import requests
import os
import json
import hashlib
from git import Repo
from git.exc import GitCommandError
import argparse

# 配置参数
SOURCE_URL = "https://raw.githubusercontent.com/vbskycn/iptv/refs/heads/master/tv/iptv4.txt"
LOCAL_FILE_PATH = "iptv4.txt"
REPO_DIR = "./jnsj_repo"
GITHUB_REPO = "cloudplains/jnsj"
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

def setup_git_repo(github_token):
    """设置 Git 仓库"""
    if not os.path.exists(REPO_DIR):
        os.makedirs(REPO_DIR)
        try:
            repo_url = f"https://{github_token}@github.com/{GITHUB_REPO}.git"
            repo = Repo.clone_from(repo_url, REPO_DIR)
            print("已克隆仓库")
        except GitCommandError as e:
            print(f"克隆仓库失败: {e}")
            return None
    else:
        try:
            repo = Repo(REPO_DIR)
            origin = repo.remote(name='origin')
            origin.pull()
            print("已拉取最新更改")
        except GitCommandError as e:
            print(f"拉取最新更改失败: {e}")
            return None
    
    return repo

def sync_file_to_github(github_token):
    """同步文件到 GitHub"""
    # 下载最新文件
    new_content = download_iptv_file()
    if new_content is None:
        return False
    
    # 设置 Git 仓库
    repo = setup_git_repo(github_token)
    if repo is None:
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
    try:
        repo.git.add(LOCAL_FILE_PATH)
        repo.index.commit(COMMIT_MSG.format(os.environ.get('GITHUB_SHA', '自动更新')))
        origin = repo.remote(name='origin')
        origin.push()
        print("已成功推送更新到 GitHub")
        return True
    except GitCommandError as e:
        print(f"提交或推送更改失败: {e}")
        return False

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