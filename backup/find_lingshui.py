import requests
import re
from concurrent.futures import ThreadPoolExecutor, as_completed
import time

def extract_urls_from_file(filename):
    """从文件中提取URL列表"""
    urls = []
    with open(filename, 'r', encoding='utf-8') as f:
        for line in f:
            line = line.strip()
            # 跳过注释行和空行
            if line and not line.startswith('#') and not line.startswith('<<<<<<<') and not line.startswith('=======') and not line.startswith('>>>>>>>'):
                # 提取URL（去掉#后面的注释）
                url = line.split('#')[0].strip()
                if url.startswith(('http://', 'https://')):
                    urls.append(url)
    return list(set(urls))  # 去重

def fetch_content(url, timeout=10):
    """获取URL内容"""
    try:
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        }
        response = requests.get(url, timeout=timeout, headers=headers)
        response.encoding = 'utf-8'
        if response.status_code == 200:
            return response.text
        else:
            print(f"请求失败: {url} - 状态码: {response.status_code}")
            return None
    except Exception as e:
        print(f"请求错误: {url} - {str(e)}")
        return None

def parse_m3u_content(content):
    """解析M3U格式内容"""
    channels = []
    lines = content.split('\n')
    channel_name = ""
    
    for line in lines:
        line = line.strip()
        if line.startswith('#EXTINF:'):
            # 提取频道名
            match = re.search(r',([^,]+)$', line)
            if match:
                channel_name = match.group(1)
        elif line.startswith('http://') or line.startswith('https://'):
            if channel_name and line:
                channels.append((channel_name, line))
                channel_name = ""
    
    return channels

def parse_txt_content(content):
    """解析TXT格式内容"""
    channels = []
    lines = content.split('\n')
    
    for line in lines:
        line = line.strip()
        if line and not line.startswith('#'):
            # 尝试多种分隔符：逗号、|、空格等
            if ',' in line:
                parts = line.split(',', 1)
                if len(parts) == 2 and parts[1].startswith(('http://', 'https://')):
                    channels.append((parts[0].strip(), parts[1].strip()))
            elif '|' in line:
                parts = line.split('|', 1)
                if len(parts) == 2 and parts[1].startswith(('http://', 'https://')):
                    channels.append((parts[0].strip(), parts[1].strip()))
            elif 'http' in line:
                # 尝试提取频道名和URL
                match = re.search(r'([^,|]+)[,|]\s*(https?://[^\s]+)', line)
                if match:
                    channels.append((match.group(1).strip(), match.group(2).strip()))
    
    return channels

def find_lingshui_channels(url):
    """从单个URL中查找包含陵水的频道"""
    print(f"正在处理: {url}")
    content = fetch_content(url)
    if not content:
        return []
    
    channels = []
    
    # 尝试解析M3U格式
    if content.startswith('#EXTM3U') or '#EXTINF:' in content:
        channels.extend(parse_m3u_content(content))
    
    # 尝试解析TXT格式
    channels.extend(parse_txt_content(content))
    
    # 过滤包含"陵水"的频道
    lingshui_channels = []
    for name, url in channels:
        if '陵水' in name:
            lingshui_channels.append((name, url))
    
    return lingshui_channels

def main():
    # 读取URL文件
    input_file = 'urls.txt'
    output_file = 'lingshui_channels.txt'
    
    print("正在提取URL列表...")
    urls = extract_urls_from_file(input_file)
    print(f"找到 {len(urls)} 个有效URL")
    
    all_lingshui_channels = []
    
    # 使用多线程加快处理速度
    print("开始搜索包含'陵水'的频道...")
    with ThreadPoolExecutor(max_workers=10) as executor:
        future_to_url = {executor.submit(find_lingshui_channels, url): url for url in urls}
        
        for future in as_completed(future_to_url):
            url = future_to_url[future]
            try:
                channels = future.result()
                if channels:
                    print(f"在 {url} 中找到 {len(channels)} 个陵水频道")
                    all_lingshui_channels.extend(channels)
            except Exception as e:
                print(f"处理 {url} 时出错: {str(e)}")
    
    # 去重
    unique_channels = list(set(all_lingshui_channels))
    
    # 写入结果文件
    with open(output_file, 'w', encoding='utf-8') as f:
        for name, url in unique_channels:
            f.write(f"{name},{url}\n")
    
    print(f"\n搜索完成！共找到 {len(unique_channels)} 个包含'陵水'的频道")
    print(f"结果已保存到: {output_file}")
    
    # 显示找到的频道
    if unique_channels:
        print("\n找到的频道列表:")
        for i, (name, url) in enumerate(unique_channels, 1):
            print(f"{i}. {name}")
    else:
        print("未找到包含'陵水'的频道")

if __name__ == "__main__":
    main()