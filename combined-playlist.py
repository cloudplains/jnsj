#!/usr/bin/env python3
"""
基于 SSH 认证的 IPTV 文件同步脚本
支持 GitHub Actions 环境和本地运行
支持多源文件同步
"""

import requests
import os
import hashlib
import subprocess
import shutil
import sys
from datetime import datetime

# 配置参数
SOURCE_URLS = [
    "https://raw.githubusercontent.com/abusaeeidx/IPTV-Scraper-Zilla/main/combined-playlist.m3u",
    "https://raw.githubusercontent.com/develop202/migu_video/refs/heads/main/interface.txt"
]
LOCAL_FILE_PATHS = {
    "combined-playlist.m3u": "combined-playlist.m3u",
    "interface.txt": "interface.txt"
}
REPO_DIR = "./jnsj_repo"
GITHUB_REPO_SSH = "git@github.com:cloudplains/jnsj.git"
GITHUB_REPO_HTTPS = "https://github.com/cloudplains/jnsj.git"
GITHUB_USERNAME = "github-actions[bot]"
GITHUB_EMAIL = "github-actions[bot]@users.noreply.github.com"
COMMIT_MSG = "🔄 自动更新 IPTV 文件 - {}"
MAX_FILE_SIZE = 50 * 1024 * 1024  # 50MB 文件大小限制

def get_file_hash(content):
    """计算文件内容的 MD5 哈希值"""
    return hashlib.md5(content.encode('utf-8')).hexdigest()

def download_iptv_files():
    """下载多个 IPTV 文件"""
    downloaded_files = {}
    
    for source_url in SOURCE_URLS:
        try:
            print(f"开始下载文件: {source_url}")
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
            }
            response = requests.get(source_url, timeout=60, headers=headers, stream=True)
            response.raise_for_status()
            
            # 检查文件大小
            content_length = response.headers.get('Content-Length')
            if content_length and int(content_length) > MAX_FILE_SIZE:
                print(f"文件过大: {content_length} bytes，跳过")
                continue
            
            content = response.text
            
            # 获取文件名
            filename = source_url.split('/')[-1]
            
            # 检查文件行数
            line_count = len(content.splitlines())
            print(f"文件 {filename} 下载成功，共 {line_count} 行")
            
            downloaded_files[filename] = content
            
        except requests.exceptions.Timeout:
            print(f"下载 {source_url} 超时")
        except requests.exceptions.RequestException as e:
            print(f"下载文件 {source_url} 失败: {e}")
        except UnicodeDecodeError:
            print(f"文件 {source_url} 编码错误")
        except Exception as e:
            print(f"处理 {source_url} 过程中发生错误: {e}")
    
    return downloaded_files

def run_command(cmd, cwd=None):
    """运行 shell 命令，返回成功状态和输出"""
    try:
        result = subprocess.run(cmd, shell=True, capture_output=True, text=True, cwd=cwd, timeout=300)
        if result.returncode != 0:
            print(f"命令执行失败: {cmd}")
            print(f"错误输出: {result.stderr}")
            return False, result.stderr
        return True, result.stdout
    except subprocess.TimeoutExpired:
        print(f"命令执行超时: {cmd}")
        return False, "Command timeout"
    except Exception as e:
        print(f"执行命令时发生异常: {e}")
        return False, str(e)

def is_git_repo(path):
    """检查路径是否是 Git 仓库"""
    return os.path.exists(os.path.join(path, '.git'))

def setup_ssh_key():
    """设置 SSH 密钥（用于本地运行）"""
    ssh_dir = os.path.expanduser("~/.ssh")
    if not os.path.exists(ssh_dir):
        os.makedirs(ssh_dir, mode=0o700)
    
    # 检查是否已配置 SSH 密钥
    private_key = os.getenv('SSH_PRIVATE_KEY')
    if private_key:
        print("检测到 SSH 私钥环境变量，配置中...")
        key_path = os.path.join(ssh_dir, 'id_rsa')
        with open(key_path, 'w') as f:
            f.write(private_key)
        os.chmod(key_path, 0o600)
        
        # 配置 SSH 已知主机
        known_hosts = os.path.join(ssh_dir, 'known_hosts')
        run_command('ssh-keyscan github.com >> ' + known_hosts)
        return True
    return False

def setup_git_repo():
    """设置 Git 仓库"""
    # 检查是否在 GitHub Actions 环境中
    is_github_actions = os.getenv('GITHUB_ACTIONS') == 'true'
    
    if is_github_actions:
        print("检测到 GitHub Actions 环境")
        REPO_DIR = "."  # 使用当前目录
    else:
        print("本地运行模式")
        # 设置 SSH 密钥
        setup_ssh_key()
        
        # 如果目录已存在，先删除
        if os.path.exists(REPO_DIR):
            print(f"删除现有目录: {REPO_DIR}")
            shutil.rmtree(REPO_DIR)
        
        os.makedirs(REPO_DIR)
        
        # 选择使用 SSH 还是 HTTPS
        repo_url = GITHUB_REPO_SSH if os.getenv('SSH_PRIVATE_KEY') else GITHUB_REPO_HTTPS
        print(f"克隆仓库: {repo_url}")
        
        success, output = run_command(f"git clone {repo_url} .", cwd=REPO_DIR)
        if not success:
            print(f"克隆仓库失败: {output}")
            return False
    
    # 配置 Git 用户信息
    run_command(f"git config user.name '{GITHUB_USERNAME}'", cwd=REPO_DIR if not is_github_actions else ".")
    run_command(f"git config user.email '{GITHUB_EMAIL}'", cwd=REPO_DIR if not is_github_actions else ".")
    
    # 拉取最新更改
    run_command("git pull origin main", cwd=REPO_DIR if not is_github_actions else ".")
    
    return True

def file_has_changes(old_content, new_content):
    """检查文件内容是否有实质性变化"""
    if old_content == new_content:
        return False
    
    # 忽略时间戳等无关变化
    old_lines = old_content.splitlines()
    new_lines = new_content.splitlines()
    
    # 过滤掉包含时间戳的行
    def filter_timestamp_lines(lines):
        return [line for line in lines if not line.strip().startswith('#EXTINF') or 'tvg-id' in line]
    
    old_filtered = filter_timestamp_lines(old_lines)
    new_filtered = filter_timestamp_lines(new_lines)
    
    return old_filtered != new_filtered

def sync_files_to_github():
    """同步多个文件到 GitHub"""
    print("开始同步流程...")
    
    # 下载最新文件
    downloaded_files = download_iptv_files()
    if not downloaded_files:
        print("下载文件失败，中止同步")
        return False
    
    # 设置 Git 仓库
    if not setup_git_repo():
        print("Git 仓库设置失败")
        return False
    
    # 确定工作目录
    is_github_actions = os.getenv('GITHUB_ACTIONS') == 'true'
    work_dir = "." if is_github_actions else REPO_DIR
    
    # 检查每个文件是否有变化并写入
    files_to_commit = []
    
    for filename, new_content in downloaded_files.items():
        local_file_path = LOCAL_FILE_PATHS.get(filename, filename)
        local_file = os.path.join(work_dir, local_file_path)
        
        # 检查文件是否已存在
        file_exists = os.path.exists(local_file)
        
        # 检查内容是否有变化
        content_changed = True
        if file_exists:
            try:
                with open(local_file, 'r', encoding='utf-8') as f:
                    old_content = f.read()
                
                content_changed = file_has_changes(old_content, new_content)
                print(f"文件 {filename} 变化检查: 是否变化={content_changed}")
            except Exception as e:
                print(f"读取旧文件 {filename} 失败: {e}")
                content_changed = True
        
        # 如果没有变化，跳过
        if not content_changed:
            print(f"文件 {filename} 内容无实质性变化，跳过")
            continue
        
        # 写入新内容
        try:
            # 确保目录存在
            os.makedirs(os.path.dirname(local_file), exist_ok=True)
            with open(local_file, 'w', encoding='utf-8') as f:
                f.write(new_content)
            print(f"文件已写入: {local_file}")
            files_to_commit.append(local_file_path)
        except Exception as e:
            print(f"写入文件 {filename} 失败: {e}")
            return False
    
    # 如果没有文件需要提交
    if not files_to_commit:
        print("所有文件均无实质性变化，无需更新")
        
        # 在 GitHub Actions 中，可以创建一个空提交来记录同步时间
        if is_github_actions:
            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            run_command(f'git commit --allow-empty -m "🔄 IPTV 文件同步检查 - 无变化 {timestamp}"', cwd=work_dir)
            run_command("git push origin main", cwd=work_dir)
            print("已创建空提交记录同步时间")
        
        return True
    
    # 提交更改
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    commit_message = COMMIT_MSG.format(timestamp)
    
    # 添加所有变更文件
    for file_path in files_to_commit:
        success, output = run_command(f"git add {file_path}", cwd=work_dir)
        if not success:
            print(f"添加文件 {file_path} 失败: {output}")
            return False
    
    # 提交更改
    success, output = run_command(f'git commit -m "{commit_message}"', cwd=work_dir)
    if not success:
        if "nothing to commit" in output:
            print("没有需要提交的更改")
            return True
        else:
            print(f"提交失败: {output}")
            return False
    
    # 推送更改
    success, output = run_command("git push origin main", cwd=work_dir)
    if not success:
        print(f"推送失败: {output}")
        return False
    
    print(f"✅ 已成功推送 {len(files_to_commit)} 个文件更新到 GitHub")
    return True

def main():
    """主函数"""
    print("=" * 50)
    print("IPTV 多文件同步脚本启动")
    print(f"开始时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 50)
    
    try:
        success = sync_files_to_github()
        if not success:
            print("❌ 同步失败")
            sys.exit(1)
        else:
            print("✅ 同步成功")
            sys.exit(0)
    except KeyboardInterrupt:
        print("\n用户中断执行")
        sys.exit(1)
    except Exception as e:
        print(f"❌ 发生未预期错误: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()