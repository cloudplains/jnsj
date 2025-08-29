import requests
from datetime import datetime
import os

# 读取assets/urls.txt
with open('assets/urls.txt', 'r') as f:
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

# 直接覆盖原文件
with open('assets/urls.txt', 'w') as f:
    for url in valid_urls:
        f.write(url + '\n')

print('Original file assets/urls.txt has been updated with valid URLs.')