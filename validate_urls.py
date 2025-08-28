import requests
from datetime import datetime
import os

# 读取urls.txt
with open('urls.txt', 'r') as f:
    urls = [line.strip() for line in f.readlines() if line.strip()]

# 验证函数
def is_url_valid(url):
    try:
        response = requests.head(url, timeout=5, allow_redirects=True)
        return response.status_code == 200
    except:
        try:
            response = requests.get(url, timeout=5, stream=True)
            return response.status_code == 200
        except:
            return False

valid_urls = []
for url in urls:
    if is_url_valid(url):
        valid_urls.append(url)
        print(f'Valid: {url}')
    else:
        print(f'Invalid: {url}')

# 生成文件名
current_time = datetime.now().strftime('%Y%m%d_%H%M%S')
output_filename = f'urls_{current_time}.txt'

# 写入有效的URL
with open(output_filename, 'w') as f:
    for url in valid_urls:
        f.write(url + '\n')

print(f'Valid URLs saved to {output_filename}')