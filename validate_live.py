import urllib.request
from urllib.parse import urlparse, quote
import re
import os
from datetime import datetime, timedelta, timezone
import socket
import ssl

# 跳过SSL证书验证
ssl._create_default_https_context = ssl._create_unverified_context

# 读取文本方法（支持多种编码）
def read_txt_to_array(file_name):
    try:
        # 先尝试 UTF-8 编码
        with open(file_name, 'r', encoding='utf-8-sig') as file:
            lines = file.readlines()
            lines = [line.strip() for line in lines]
            return lines
    except UnicodeDecodeError:
        try:
            # 如果 UTF-8 失败，尝试 GBK 编码
            with open(file_name, 'r', encoding='gbk') as file:
                lines = file.readlines()
                lines = [line.strip() for line in lines]
                return lines
        except UnicodeDecodeError:
            try:
                # 如果 GBK 也失败，尝试 latin-1 编码
                with open(file_name, 'r', encoding='latin-1') as file:
                    lines = file.readlines()
                    lines = [line.strip() for line in lines]
                    return lines
            except Exception as e:
                print(f"无法确定合适的编码格式进行解码文件: {file_name}, 错误: {e}")
                return []
    except FileNotFoundError:
        print(f"File '{file_name}' not found.")
        return []
    except Exception as e:
        print(f"读取文件 {file_name} 时发生错误: {e}")
        return []

# 直播源验证函数
def validate_stream_url(url, timeout=3):
    """
    验证直播源是否可访问
    """
    try:
        # 解析URL获取主机和端口
        parsed_url = urlparse(url)
        host = parsed_url.hostname
        port = parsed_url.port or (443 if parsed_url.scheme == 'https' else 80)
        
        # 首先尝试TCP连接测试
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(timeout)
        result = sock.connect_ex((host, port))
        sock.close()
        
        if result != 0:
            return False  # TCP连接失败
            
        # 对于HTTP/HTTPS协议，进行更详细的验证
        if url.startswith(('http://', 'https://')):
            try:
                headers = {
                    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
                    'Accept': '*/*',
                    'Connection': 'close',
                    'Range': 'bytes=0-1024'  # 只请求少量数据以验证
                }
                
                req = urllib.request.Request(url, headers=headers)
                with urllib.request.urlopen(req, timeout=timeout) as response:
                    # 检查状态码
                    if response.getcode() not in [200, 206]:
                        return False
                    
                    # 检查内容类型
                    content_type = response.headers.get('Content-Type', '')
                    if not any(x in content_type for x in ['video', 'audio', 'application/octet-stream', 'application/vnd.apple.mpegurl']):
                        return False
                        
            except urllib.error.HTTPError as e:
                # 对于部分HTTP错误，仍然可能是可用的流
                if e.code in [200, 206, 301, 302, 307]:
                    return True
                return False
            except Exception:
                return False
                
        return True
        
    except Exception:
        return False

# 处理直播源文件
def process_live_file(input_file, output_file):
    print(f"开始处理直播源文件: {input_file}")
    
    # 读取原始文件
    lines = read_txt_to_array(input_file)
    if not lines:
        print("文件为空或读取失败")
        return
    
    # 获取当前的 UTC 时间
    utc_time = datetime.now(timezone.utc)
    beijing_time = utc_time + timedelta(hours=8)
    formatted_time = beijing_time.strftime("%Y-%m-%d %H:%M")
    
    # 有效行列表
    valid_lines = []
    
    # 处理每一行
    for line in lines:
        # 跳过空行和注释行
        if not line.strip() or line.startswith('#') or 'genre' in line.lower():
            continue
            
        # 检查是否为标准格式（频道名称,URL）
        if ',' in line and '://' in line:
            parts = line.split(',', 1)
            channel_name = parts[0].strip()
            url = parts[1].strip()
            
            # 验证URL有效性
            if validate_stream_url(url):
                valid_lines.append(f"{channel_name},{url}")
                print(f"有效: {channel_name}")
            else:
                print(f"无效: {channel_name} - {url}")
        else:
            print(f"跳过不规则格式: {line}")
    
    # 添加更新时间标记
    valid_lines.insert(0, f"# 更新时间: {formatted_time}")
    
    # 写入新文件
    try:
        with open(output_file, 'w', encoding='utf-8') as f:
            for line in valid_lines:
                f.write(line + '\n')
        print(f"已保存有效直播源到: {output_file}")
        print(f"原始行数: {len(lines)}, 有效行数: {len(valid_lines)}")
    except Exception as e:
        print(f"保存文件时发生错误：{e}")

# 主函数
if __name__ == "__main__":
    # 执行开始时间
    timestart = datetime.now()
    
    # 输入和输出文件
    input_file = "assets/live.txt"
    output_file = "assets/live.txt"  # 覆盖原文件
    
    # 处理直播源文件
    process_live_file(input_file, output_file)
    
    # 执行结束时间
    timeend = datetime.now()
    elapsed_time = timeend - timestart
    total_seconds = elapsed_time.total_seconds()
    minutes = int(total_seconds // 60)
    seconds = int(total_seconds % 60)
    
    print(f"执行时间: {minutes} 分 {seconds} 秒")