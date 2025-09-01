import requests
import os
import argparse
import re

# 配置 GitHub Token，需要有 repo 权限
GITHUB_TOKEN = os.getenv('GITHUB_TOKEN')
HEADERS = {'Authorization': f'token {GITHUB_TOKEN}'} if GITHUB_TOKEN else {}
GITHUB_API_BASE = "https://api.github.com"

def get_latest_release(repo_owner, repo_name):
    """
    获取指定仓库的最新发布版本信息
    """
    url = f"{GITHUB_API_BASE}/repos/{repo_owner}/{repo_name}/releases/latest"
    response = requests.get(url, headers=HEADERS)
    response.raise_for_status()
    return response.json()

def download_asset(asset_url, destination_path, asset_name=None):
    """
    下载指定的资产文件
    """
    if not asset_name:
        asset_name = os.path.basename(asset_url)
    
    os.makedirs(destination_path, exist_ok=True)
    local_filename = os.path.join(destination_path, asset_name)
    
    print(f"正在下载: {asset_name}")
    with requests.get(asset_url, headers=HEADERS, stream=True) as r:
        r.raise_for_status()
        with open(local_filename, 'wb') as f:
            for chunk in r.iter_content(chunk_size=8192):
                f.write(chunk)
    print(f"下载完成: {local_filename}")
    return local_filename

def get_repo_info_from_url(repo_url):
    """
    从 GitHub URL 中提取仓库所有者和名称
    """
    pattern = r"github\.com/([^/]+)/([^/]+)"
    match = re.search(pattern, repo_url)
    if match:
        return match.group(1), match.group(2)
    raise ValueError("无效的 GitHub URL")

def main():
    parser = argparse.ArgumentParser(description='同步 GitHub Release 资源')
    parser.add_argument('--repo-url', help='GitHub 仓库 URL，例如: https://github.com/Guovin/iptv-api')
    parser.add_argument('--repo', help='格式: owner/repo_name')
    parser.add_argument('--dest-dir', default='./downloads', help='下载文件保存目录')
    
    args = parser.parse_args()
    
    if args.repo_url:
        repo_owner, repo_name = get_repo_info_from_url(args.repo_url)
    elif args.repo:
        repo_owner, repo_name = args.repo.split('/')
    else:
        raise ValueError("必须提供 --repo-url 或 --repo 参数")
    
    try:
        # 获取最新发布信息
        release_info = get_latest_release(repo_owner, repo_name)
        tag_name = release_info['tag_name']
        assets = release_info.get('assets', [])
        
        print(f"仓库: {repo_owner}/{repo_name}")
        print(f"最新发布版本: {tag_name}")
        print(f"资源文件数量: {len(assets)}")
        
        # 下载所有 zip 资源文件
        zip_assets = [asset for asset in assets if asset['name'].endswith('.zip')]
        downloaded_files = []
        
        for asset in zip_assets:
            file_path = download_asset(asset['url'], args.dest_dir, asset['name'])
            downloaded_files.append(file_path)
            
        print(f"成功下载 {len(zip_assets)} 个 zip 文件")
        return downloaded_files
        
    except requests.exceptions.HTTPError as e:
        print(f"HTTP 错误: {e}")
        if e.response.status_code == 404:
            print("未找到仓库或发布信息，请检查仓库名称和权限设置")
    except Exception as e:
        print(f"发生错误: {e}")

if __name__ == "__main__":
    main()