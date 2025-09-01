import requests
import json
from datetime import datetime
import os
import time

def is_url_valid(url, timeout=5):
    """检查URL是否可访问"""
    try:
        # 处理特殊协议
        if url.startswith('clan://'):
            return True  # 本地配置，默认视为有效
            
        response = requests.head(url, timeout=timeout, allow_redirects=True)
        return response.status_code < 400
    except requests.RequestException:
        try:
            # 如果HEAD失败，尝试GET请求
            response = requests.get(url, timeout=timeout, allow_redirects=True)
            return response.status_code < 400
        except requests.RequestException:
            return False

def validate_txt_urls():
    """验证assets/urls.txt中的URL"""
    try:
        # 读取assets/urls.txt
        with open('assets/urls.txt', 'r') as f:
            urls = [line.strip() for line in f.readlines() if line.strip()]

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
        with open('assets/urls.txt', 'w') as f:
            f.write(header)
            for url in valid_urls:
                f.write(url + '\n')

        print('assets/urls.txt has been updated with valid URLs.')
        
    except Exception as e:
        print(f"处理assets/urls.txt时出错: {e}")

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
    validate_txt_urls()
    print("\n开始验证jnsj.json...")
    validate_json_urls()
    print("\nURL验证完成!")