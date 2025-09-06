# validate_urls.py
import requests
import json
from datetime import datetime
import os
import time

def is_url_valid(url, timeout=5):
    """检查URL是否可访问"""
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
    }
    
    try:
        # 处理特殊协议
        if url.startswith('clan://'):
            return True  # 本地配置，默认视为有效
            
        # 首先尝试HEAD请求
        response = requests.head(url, headers=headers, timeout=timeout, allow_redirects=True)
        if response.status_code < 400:
            return True
            
    except requests.RequestException:
        try:
            # 如果HEAD失败，尝试GET请求（但只获取头部信息）
            response = requests.get(url, headers=headers, timeout=timeout, allow_redirects=True, stream=True)
            # 只读取前几个字节来确认连接
            for _ in response.iter_content(1024):
                break
            return response.status_code < 400
        except requests.RequestException:
            # 尝试更宽松的验证方式
            try:
                # 尝试建立连接但不读取数据
                response = requests.get(url, headers=headers, timeout=timeout, allow_redirects=True, stream=True)
                return response.status_code < 400
            except:
                return False
    return False

def read_txt_file(file_path, is_live_format=False):
    """读取TXT文件，处理可能的BOM和注释"""
    urls = []
    try:
        # 以二进制方式读取文件来处理BOM
        with open(file_path, 'rb') as f:
            content = f.read()
            
        # 检查并移除BOM
        if content.startswith(b'\xef\xbb\xbf'):
            content = content[3:]
            
        # 解码内容
        content = content.decode('utf-8')
        
        # 处理每行内容
        for line in content.splitlines():
            line = line.strip()
            # 跳过空行和注释行
            if line and not line.startswith('#'):
                # 对于live.txt文件，只处理"频道名称,URL"格式的行
                if is_live_format:
                    if ',' in line:
                        # 提取URL部分（最后一个逗号后的内容）
                        url = line.split(',')[-1].strip()
                        if url and not url.startswith('#'):
                            urls.append(url)
                    # 如果不是"频道名称,URL"格式，直接跳过（不保留）
                else:
                    # 对于urls.txt文件，直接添加URL
                    urls.append(line)
                    
    except Exception as e:
        print(f"读取文件 {file_path} 时出错: {e}")
        
    return urls

def validate_txt_urls(input_file, output_file, is_live_format=False):
    """验证TXT文件中的URL"""
    try:
        urls = read_txt_file(input_file, is_live_format)
        valid_urls = []
        
        for url in urls:
            if is_url_valid(url):
                valid_urls.append(url)
                print(f'Valid: {url}')
            else:
                print(f'Invalid: {url}')
            
            # 添加延迟，避免请求过于频繁
            time.sleep(0.5)

        # 添加更新时间标记
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        header = f"# 更新时间: {timestamp}\n# 有效URL数量: {len(valid_urls)}\n\n"
        
        # 直接覆盖原文件
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write(header)
            for url in valid_urls:
                f.write(url + '\n')

        print(f'{output_file} has been updated with valid URLs.')
        
    except Exception as e:
        print(f"处理 {input_file} 时出错: {e}")

def validate_json_urls():
    """验证jnsj.json中的URL"""
    try:
        # 读取原始文件，处理可能的BOM
        with open('jnsj.json', 'rb') as f:
            content = f.read()
            
        # 检查并移除BOM
        if content.startswith(b'\xef\xbb\xbf'):
            content = content[3:]
            
        # 解析JSON
        data = json.loads(content.decode('utf-8'))
        
        # 验证每个URL
        valid_urls = []
        for item in data.get('urls', []):
            url = item.get('url', '')
            name = item.get('name', '')
            
            print(f"验证: {name} - {url}")
            
            if is_url_valid(url):
                valid_urls.append(item)
                print(f"√ {name} 有效")
            else:
                print(f"× {name} 无效")
            
            # 添加延迟，避免请求过于频繁
            time.sleep(0.5)
        
        # 更新数据并添加更新时间标记
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        data['urls'] = valid_urls
        data['last_updated'] = timestamp
        data['valid_count'] = len(valid_urls)
        
        # 写回文件（不包含BOM）
        with open('jnsj.json', 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
            
        print(f"jnsj.json 已更新，有效URL数量: {len(valid_urls)}")
        
    except Exception as e:
        print(f"处理jnsj.json时出错: {e}")

if __name__ == "__main__":
    print("开始验证URLs...")
    validate_txt_urls('assets/urls.txt', 'assets/urls.txt')
    print("\n开始验证live.txt...")
    validate_txt_urls('assets/live.txt', 'assets/live.txt', is_live_format=True)
    print("\n开始验证jnsj.json...")
    validate_json_urls()
    print("\nURL验证完成!")
