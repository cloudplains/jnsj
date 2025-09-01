import requests
import os
from urllib.parse import urljoin
import argparse

# 配置GitHub Token，需要有repo权限
GITHUB_TOKEN = os.getenv('GITHUB_TOKEN')
HEADERS = {'Authorization': f'token {GITHUB_TOKEN}'} if GITHUB_TOKEN else {}

def get_latest_release(repo_owner, repo_name):
    """
    获取指定仓库的最新发布版本信息
    """
    url = f"https://api.github.com/repos/{repo_owner}/{repo_name}/releases/latest"
    response = requests.get(url, headers=HEADERS)
    response.raise_for_status()
    return response.json()

def download_asset(asset_url, destination_path, asset_name=None):
    """
    下载指定的资产文件
    """
    if not asset_name:
        asset_name = os.path.basename(asset_url)
    
    local_filename = os.path.join(destination_path, asset_name)
    os.makedirs(destination_path, exist_ok=True)
    
    print(f"正在下载: {asset_name}")
    with requests.get(asset_url, headers=HEADERS, stream=True) as r:
        r.raise_for_status()
        with open(local_filename, 'wb') as f:
            for chunk in r.iter_content(chunk_size=8192):
                f.write(chunk)
    print(f"下载完成: {local_filename}")
    return local_filename

def main():
    parser = argparse.ArgumentParser(description='同步GitHub Release资源')
    parser.add_argument('--repo', required=True, help='格式: owner/repo_name')
    parser.add_argument('--dest-dir', default='./downloads', help='下载文件保存目录')
    
    args = parser.parse_args()
    repo_owner, repo_name = args.repo.split('/')
    
    try:
        # 获取最新发布信息
        release_info = get_latest_release(repo_owner, repo_name)
        tag_name = release_info['tag_name']
        assets = release_info.get('assets', [])
        
        print(f"找到发布版本: {tag_name}")
        print(f"资源文件数量: {len(assets)}")
        
        # 下载所有zip资源文件
        zip_assets = [asset for asset in assets if asset['name'].endswith('.zip')]
        for asset in zip_assets:
            download_asset(asset['url'], args.dest_dir, asset['name'])
            
    except requests.exceptions.HTTPError as e:
        print(f"HTTP错误: {e}")
    except Exception as e:
        print(f"发生错误: {e}")

if __name__ == "__main__":
    main()