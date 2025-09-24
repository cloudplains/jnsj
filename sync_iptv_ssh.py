#!/usr/bin/env python3
"""
基于 SSH 认证的 IPTV 文件同步脚本
支持 GitHub Actions 环境和本地运行
添加源有效性验证功能
"""

import requests
import os
import hashlib
import subprocess
import shutil
import sys
import re
import concurrent.futures
from datetime import datetime
from urllib.parse import urlparse
import time

# 配置参数
SOURCE_URL = "https://raw.githubusercontent.com/abusaeeidx/IPTV-Scraper-Zilla/main/combined-playlist.m3u"
LOCAL_FILE_PATH = "combined-playlist.m3u"
REPO_DIR = "./jnsj_repo"
GITHUB_REPO_SSH = "git@github.com:cloudplains/jnsj.git"
GITHUB_REPO_HTTPS = "https://github.com/cloudplains/jnsj.git"
GITHUB_USERNAME = "github-actions[bot]"
GITHUB_EMAIL = "github-actions[bot]@users.noreply.github.com"
COMMIT_MSG = "🔄 自动更新 IPTV 文件 - {}"
MAX_FILE_SIZE = 50 * 1024 * 1024  # 50MB 文件大小限制

# 源验证配置
VALIDATION_TIMEOUT = 10  # 每个源的验证超时时间（秒）
MIN_VALID_SOURCES = 10   # 最小有效源数量阈值
VALIDATION_WORKERS = 5   # 并发验证的工作线程数
VALIDATION_SAMPLE_SIZE = 50  # 随机抽样的源数量（如果源太多）

def get_file_hash(content):
    """计算文件内容的 MD5 哈希值"""
    return hashlib.md5(content.encode('utf-8')).hexdigest()

def parse_m3u_content(content):
    """解析 M3U 内容，提取频道信息"""
    channels = []
    lines = content.splitlines()
    
    i = 0
    while i < len(lines):
        line = lines[i].strip()
        if line.startswith('#EXTINF:'):
            # 提取频道信息
            extinf_line = line
            i += 1
            if i < len(lines):
                url_line = lines[i].strip()
                if url_line and not url_line.startswith('#'):
                    # 解析 EXTINF 行
                    match = re.search(r'#EXTINF:(-1|\d+)\s*(.*?),(.*)', extinf_line)
                    if match:
                        duration = match.group(1)
                        attributes = match.group(2)
                        name = match.group(3)
                        
                        # 提取属性
                        tvg_id = re.search(r'tvg-id="([^"]*)"', attributes)
                        tvg_name = re.search(r'tvg-name="([^"]*)"', attributes)
                        tvg_logo = re.search(r'tvg-logo="([^"]*)"', attributes)
                        group_title = re.search(r'group-title="([^"]*)"', attributes)
                        
                        channels.append({
                            'name': name,
                            'url': url_line,
                            'duration': duration,
                            'tvg_id': tvg_id.group(1) if tvg_id else '',
                            'tvg_name': tvg_name.group(1) if tvg_name else name,
                            'tvg_logo': tvg_logo.group(1) if tvg_logo else '',
                            'group_title': group_title.group(1) if group_title else '',
                            'attributes': attributes,
                            'extinf_line': extinf_line
                        })
        i += 1
    
    return channels

def validate_source(channel):
    """验证单个播放源是否有效"""
    url = channel['url']
    
    # 跳过明显无效的URL
    if not url or url.startswith('#') or '://' not in url:
        return False, channel, "无效的URL格式"
    
    try:
        # 对于不同的协议使用不同的验证方法
        if url.startswith('http'):
            # HTTP流媒体验证
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
                'Range': 'bytes=0-1000'  # 只请求部分内容
            }
            
            response = requests.get(url, timeout=VALIDATION_TIMEOUT, headers=headers, stream=True)
            if response.status_code in [200, 206]:
                # 检查内容类型
                content_type = response.headers.get('content-type', '').lower()
                if any(x in content_type for x in ['video', 'audio', 'application/octet-stream']):
                    return True, channel, "有效"
                else:
                    # 也可能是文本格式的m3u8，继续检查
                    return True, channel, "有效（非标准内容类型）"
            else:
                return False, channel, f"HTTP错误: {response.status_code}"
                
        elif url.startswith('rtmp') or url.startswith('rtsp'):
            # RTMP/RTSP流媒体 - 简单验证URL格式
            # 实际验证需要专用客户端，这里只做格式检查
            return True, channel, "RTMP/RTSP格式有效"
            
        else:
            # 其他协议暂不验证
            return True, channel, "其他协议"
            
    except requests.exceptions.Timeout:
        return False, channel, "连接超时"
    except requests.exceptions.ConnectionError:
        return False, channel, "连接错误"
    except requests.exceptions.RequestException as e:
        return False, channel, f"请求异常: {str(e)}"
    except Exception as e:
        return False, channel, f"验证异常: {str(e)}"

def validate_iptv_sources(content):
    """验证IPTV源的有效性，返回过滤后的内容"""
    print("开始验证IPTV源有效性...")
    
    # 解析M3U内容
    channels = parse_m3u_content(content)
    print(f"解析到 {len(channels)} 个频道")
    
    if len(channels) == 0:
        print("未找到有效的频道信息")
        return content  # 返回原内容
    
    # 如果频道数量太多，进行随机抽样验证
    channels_to_validate = channels
    if len(channels) > VALIDATION_SAMPLE_SIZE:
        print(f"频道数量过多 ({len(channels)})，随机抽样 {VALIDATION_SAMPLE_SIZE} 个进行验证")
        import random
        channels_to_validate = random.sample(channels, VALIDATION_SAMPLE_SIZE)
    
    print(f"正在验证 {len(channels_to_validate)} 个源...")
    
    valid_channels = []
    invalid_channels = []
    
    # 使用线程池并发验证
    with concurrent.futures.ThreadPoolExecutor(max_workers=VALIDATION_WORKERS) as executor:
        future_to_channel = {executor.submit(validate_source, channel): channel for channel in channels_to_validate}
        
        for i, future in enumerate(concurrent.futures.as_completed(future_to_channel)):
            channel = future_to_channel[future]
            try:
                is_valid, validated_channel, message = future.result()
                if is_valid:
                    valid_channels.append(validated_channel)
                    print(f"✅ [{i+1}/{len(channels_to_validate)}] 有效: {validated_channel['name']}")
                else:
                    invalid_channels.append(validated_channel)
                    print(f"❌ [{i+1}/{len(channels_to_validate)}] 无效: {validated_channel['name']} - {message}")
            except Exception as e:
                invalid_channels.append(channel)
                print(f"❌ [{i+1}/{len(channels_to_validate)}] 验证异常: {channel['name']} - {str(e)}")
            
            # 添加小延迟避免请求过于频繁
            time.sleep(0.1)
    
    print(f"验证完成: {len(valid_channels)} 个有效, {len(invalid_channels)} 个无效")
    
    # 计算有效比例
    total_validated = len(valid_channels) + len(invalid_channels)
    if total_validated > 0:
        valid_ratio = len(valid_channels) / total_validated
        print(f"有效比例: {valid_ratio:.1%}")
    else:
        valid_ratio = 0
    
    # 如果有效源太少，返回原始内容（可能是验证环境问题）
    if len(valid_channels) < MIN_VALID_SOURCES:
        print(f"警告: 有效源数量 ({len(valid_channels)}) 低于阈值 ({MIN_VALID_SOURCES})，保留所有源")
        return content
    
    # 根据抽样验证结果过滤所有频道
    if len(channels_to_validate) < len(channels):
        print("根据抽样结果过滤所有频道...")
        # 构建有效URL的模式（基于抽样结果）
        valid_patterns = set()
        for channel in valid_channels:
            # 提取域名或特征模式
            url = channel['url']
            if '://' in url:
                domain = url.split('://')[1].split('/')[0]
                valid_patterns.add(domain)
        
        filtered_channels = []
        for channel in channels:
            url = channel['url']
            if any(pattern in url for pattern in valid_patterns):
                filtered_channels.append(channel)
        
        print(f"过滤后保留 {len(filtered_channels)} 个频道")
        channels = filtered_channels
    else:
        # 全部验证过，直接使用有效频道
        channels = valid_channels
    
    # 重新构建M3U内容
    new_content = "#EXTM3U\n"
    for channel in channels:
        new_content += f"{channel['extinf_line']}\n"
        new_content += f"{channel['url']}\n"
    
    return new_content

def download_iptv_file():
    """下载 IPTV 文件，包含错误处理和验证"""
    try:
        print(f"开始下载 IPTV 文件: {SOURCE_URL}")
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        }
        response = requests.get(SOURCE_URL, timeout=60, headers=headers, stream=True)
        response.raise_for_status()
        
        # 检查文件大小
        content_length = response.headers.get('Content-Length')
        if content_length and int(content_length) > MAX_FILE_SIZE:
            print(f"文件过大: {content_length} bytes")
            return None
        
        content = response.text
        
        # 基本验证：确保是有效的 M3U 文件
        if not content.startswith('#EXTM3U'):
            print("下载的文件不是有效的 M3U 格式")
            return None
        
        # 检查文件行数
        line_count = len(content.splitlines())
        print(f"文件下载成功，共 {line_count} 行")
        
        # 添加源有效性验证
        validated_content = validate_iptv_sources(content)
        
        # 比较验证前后的变化
        original_channels = len(parse_m3u_content(content))
        validated_channels = len(parse_m3u_content(validated_content))
        
        print(f"源验证结果: {original_channels} -> {validated_channels} 个频道")
        
        return validated_content
        
    except requests.exceptions.Timeout:
        print("下载超时")
        return None
    except requests.exceptions.RequestException as e:
        print(f"下载文件失败: {e}")
        return None
    except UnicodeDecodeError:
        print("文件编码错误")
        return None
    except Exception as e:
        print(f"源验证过程中发生错误: {e}")
        # 验证失败时返回原始内容
        return content

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

def sync_file_to_github():
    """同步文件到 GitHub"""
    print("开始同步流程...")
    
    # 下载最新文件（包含源验证）
    new_content = download_iptv_file()
    if new_content is None:
        print("下载文件失败，中止同步")
        return False
    
    # 设置 Git 仓库
    if not setup_git_repo():
        print("Git 仓库设置失败")
        return False
    
    # 确定工作目录
    is_github_actions = os.getenv('GITHUB_ACTIONS') == 'true'
    work_dir = "." if is_github_actions else REPO_DIR
    local_file = os.path.join(work_dir, LOCAL_FILE_PATH)
    
    # 检查文件是否已存在
    file_exists = os.path.exists(local_file)
    
    # 检查内容是否有变化
    content_changed = True
    if file_exists:
        try:
            with open(local_file, 'r', encoding='utf-8') as f:
                old_content = f.read()
            
            content_changed = file_has_changes(old_content, new_content)
            print(f"文件变化检查: 是否变化={content_changed}")
        except Exception as e:
            print(f"读取旧文件失败: {e}")
            content_changed = True
    
    # 如果没有变化，则不需要提交
    if not content_changed:
        print("文件内容无实质性变化，无需更新")
        
        # 在 GitHub Actions 中，可以创建一个空提交来记录同步时间
        if is_github_actions:
            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            run_command(f'git commit --allow-empty -m "🔄 IPTV 文件同步检查 - 无变化 {timestamp}"', cwd=work_dir)
            run_command("git push origin main", cwd=work_dir)
            print("已创建空提交记录同步时间")
        
        return True
    
    # 写入新内容
    try:
        with open(local_file, 'w', encoding='utf-8') as f:
            f.write(new_content)
        print(f"文件已写入: {local_file}")
    except Exception as e:
        print(f"写入文件失败: {e}")
        return False
    
    # 提交更改
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    commit_message = COMMIT_MSG.format(timestamp)
    
    # 添加文件
    success, output = run_command(f"git add {LOCAL_FILE_PATH}", cwd=work_dir)
    if not success:
        print(f"添加文件失败: {output}")
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
    
    print("✅ 已成功推送更新到 GitHub")
    return True

def main():
    """主函数"""
    print("=" * 50)
    print("IPTV 文件同步脚本启动（带源验证功能）")
    print(f"开始时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 50)
    
    try:
        success = sync_file_to_github()
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