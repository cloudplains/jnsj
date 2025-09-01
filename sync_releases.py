import requests
import os
import argparse
import re
import json
from typing import List, Tuple
from urllib.parse import urlparse

GITHUB_TOKEN = os.getenv('GITHUB_TOKEN')
HEADERS = {'Authorization': f'token {GITHUB_TOKEN}'} if GITHUB_TOKEN else {}
GITHUB_API_BASE = "https://api.github.com"

def get_latest_release(repo_owner, repo_name):
    """获取指定仓库的最新发布版本信息"""
    url = f"{GITHUB_API_BASE}/repos/{repo_owner}/{repo_name}/releases/latest"
    response = requests.get(url, headers=HEADERS)
    
    if response.status_code != 200:
        if response.status_code == 404:
            return get_latest_tag(repo_owner, repo_name)
        response.raise_for_status()
    
    return response.json()

def get_latest_tag(repo_owner, repo_name):
    """获取指定仓库的最新标签信息"""
    url = f"{GITHUB_API_BASE}/repos/{repo_owner}/{repo_name}/tags"
    response = requests.get(url, headers=HEADERS)
    
    if response.status_code != 200:
        response.raise_for_status()
    
    tags = response.json()
    if not tags:
        return None
    
    return {
        'tag_name': tags[0]['name'],
        'assets': [],
        'is_tag': True
    }

def download_asset(asset_url, destination_path, asset_name):
    """下载指定的资产文件"""
    os.makedirs(destination_path, exist_ok=True)
    local_filename = os.path.join(destination_path, asset_name)
    
    download_headers = HEADERS.copy()
    download_headers['Accept'] = 'application/octet-stream'
    
    try:
        with requests.get(asset_url, headers=download_headers, stream=True) as r:
            r.raise_for_status()
            with open(local_filename, 'wb') as f:
                for chunk in r.iter_content(chunk_size=8192):
                    f.write(chunk)
        
        file_size = os.path.getsize(local_filename)
        if file_size > 0:
            print(f"✅ 下载完成: {local_filename} (大小: {file_size} 字节)")
            return local_filename, file_size
        else:
            print(f"❌ 文件为空: {local_filename}")
            os.remove(local_filename)
            return None, 0
            
    except Exception as e:
        print(f"❌ 下载失败: {asset_url} - {str(e)}")
        return None, 0

def get_repo_info_from_url(repo_url):
    """从 GitHub URL 中提取仓库所有者和名称"""
    parsed = urlparse(repo_url)
    path_parts = parsed.path.strip('/').split('/')
    
    if len(path_parts) < 2:
        raise ValueError("无效的 GitHub URL")
    
    return path_parts[0], path_parts[1]

def process_repository(repo_owner, repo_name, dest_dir):
    """处理单个仓库的发布同步"""
    try:
        print(f"\n🔍 开始处理仓库: {repo_owner}/{repo_name}")
        
        release_info = get_latest_release(repo_owner, repo_name)
        if not release_info:
            print(f"⚠️ 未找到 {repo_owner}/{repo_name} 的发布或标签")
            return []
        
        tag_name = release_info['tag_name']
        print(f"🏷️ 最新版本: {tag_name}")
        
        downloaded_files = []
        
        # 处理 nginx 特殊情况
        if repo_owner == "nginx" and repo_name == "nginx":
            download_url = f"https://github.com/nginx/nginx/archive/refs/tags/{tag_name}.tar.gz"
            asset_name = f"nginx-{tag_name.replace('release-', '')}.tar.gz"
            
            repo_dir = os.path.join(dest_dir, f"{repo_owner}_{repo_name}")
            file_path, file_size = download_asset(download_url, repo_dir, asset_name)
            if file_path:
                downloaded_files.append((file_path, file_size))
            return downloaded_files
        
        # 处理普通仓库的发布资源
        assets = release_info.get('assets', [])
        if not assets and 'is_tag' in release_info:
            download_url = f"https://github.com/{repo_owner}/{repo_name}/archive/refs/tags/{tag_name}.tar.gz"
            asset_name = f"{repo_name}-{tag_name}.tar.gz"
            
            repo_dir = os.path.join(dest_dir, f"{repo_owner}_{repo_name}")
            file_path, file_size = download_asset(download_url, repo_dir, asset_name)
            if file_path:
                downloaded_files.append((file_path, file_size))
            return downloaded_files
        
        # 下载所有资源文件
        for asset in assets:
            if any(asset['name'].endswith(ext) for ext in ['.zip', '.tar.gz', '.tgz', '.tar.bz2']):
                repo_dir = os.path.join(dest_dir, f"{repo_owner}_{repo_name}")
                file_path, file_size = download_asset(asset['url'], repo_dir, asset['name'])
                if file_path:
                    downloaded_files.append((file_path, file_size))
        
        return downloaded_files
        
    except Exception as e:
        print(f"🔥 处理仓库 {repo_owner}/{repo_name} 时发生错误: {str(e)}")
        return []

def main():
    parser = argparse.ArgumentParser(description='同步 GitHub Release 资源')
    parser.add_argument('--repo-list', required=True, help='包含多个仓库的 JSON 文件路径')
    parser.add_argument('--dest-dir', default='./downloads', help='下载文件保存目录')
    
    args = parser.parse_args()
    
    all_downloaded_files = []
    
    try:
        with open(args.repo_list, 'r') as f:
            repos = json.load(f)
        
        print(f"🔄 开始同步 {len(repos)} 个仓库的发布")
        
        for repo in repos:
            if 'url' in repo:
                repo_owner, repo_name = get_repo_info_from_url(repo['url'])
            elif 'repo' in repo:
                repo_owner, repo_name = repo['repo'].split('/')
            else:
                continue
            
            files = process_repository(repo_owner, repo_name, args.dest_dir)
            all_downloaded_files.extend(files)
            
    except Exception as e:
        print(f"🚨 处理仓库列表时发生错误: {str(e)}")
        return []
    
    valid_files = [f for f in all_downloaded_files if f[0] is not None]
    print(f"\n✅ 同步完成! 总共下载了 {len(valid_files)} 个有效文件")
    return valid_files

if __name__ == "__main__":
    main()