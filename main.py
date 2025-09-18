import urllib.request
from urllib.parse import urlparse, quote
import re
import os
from datetime import datetime, timedelta, timezone
import random
import opencc
import ssl
import sys
import socket
import time
import concurrent.futures
import threading

# 跳过SSL证书验证
ssl._create_default_https_context = ssl._create_unverified_context

# 执行开始时间
timestart = datetime.now()

# 设置标准输出和错误输出立即刷新
sys.stdout = os.fdopen(sys.stdout.fileno(), 'w', 1)
sys.stderr = os.fdopen(sys.stderr.fileno(), 'w', 1)

print("脚本开始执行")

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

# 读取黑名单（支持多种编码）
def read_blacklist_from_txt(file_path):
    blacklist = []
    try:
        # 先尝试 UTF-8 编码
        with open(file_path, 'r', encoding='utf-8-sig') as file:
            lines = file.readlines()
    except UnicodeDecodeError:
        try:
            # 如果 UTF-8 失败，尝试 GBK 编码
            with open(file_path, 'r', encoding='gbk') as file:
                lines = file.readlines()
        except UnicodeDecodeError:
            try:
                # 如果 GBK 也失败，尝试 latin-1 编码
                with open(file_path, 'r', encoding='latin-1') as file:
                    lines = file.readlines()
            except Exception as e:
                print(f"读取黑名单时出错: {e}")
                return []

    # 提取URL部分（逗号后的部分）
    for line in lines:
        line = line.strip()
        if ',' in line:
            url = line.split(',')[1].strip()
            blacklist.append(url)
        else:
            blacklist.append(line)
    return blacklist

# 读取白名单（支持多种编码）
def read_whitelist_from_txt(file_path):
    try:
        # 先尝试 UTF-8 编码
        with open(file_path, 'r', encoding='utf-8-sig') as file:
            lines = file.readlines()
    except UnicodeDecodeError:
        try:
            # 如果 UTF-8 失败，尝试 GBK 编码
            with open(file_path, 'r', encoding='gbk') as file:
                lines = file.readlines()
        except UnicodeDecodeError:
            try:
                # 如果 GBK 也失败，尝试 latin-1 编码
                with open(file_path, 'r', encoding='latin-1') as file:
                    lines = file.readlines()
            except Exception as e:
                print(f"读取白名单时出错: {e}")
                return []

    # 从每行提取URL部分（逗号后的部分）
    WhiteList = []
    for line in lines:
        line = line.strip()
        if ',' in line:
            url = line.split(',')[1].strip()
            WhiteList.append(url)
        else:
            WhiteList.append(line)
    return WhiteList

print("正在读取黑名单...")
blacklist_auto = read_blacklist_from_txt('assets/whitelist-blacklist/blacklist_auto.txt')
black_list_manual = read_blacklist_from_txt('assets/whitelist-blacklist/blacklist_manual.txt')
combined_blacklist = set(blacklist_auto + black_list_manual)
print(f"合并黑名单行数: {len(combined_blacklist)}")

# 打印一些黑名单URL示例
print("黑名单示例:")
for i, url in enumerate(list(combined_blacklist)[:5]):
    print(f"  {i+1}. {url}")

print("正在读取白名单...")
whitelist = read_whitelist_from_txt('assets/whitelist-blacklist/whitelist.txt')
print(f"白名单行数: {len(whitelist)}")
for url in whitelist:
    print(f"白名单URL: {url}")

# 定义多个对象用于存储不同内容的行文本
zh_lines = []  # 综合频道
ys_lines = []  # 央视频道
ws_lines = []  # 卫视频道
dy_lines = []  # 电影频道
gj_lines = []  # 国际台
zb_lines = []  # 直播中国
gd_lines = []  # 地方台-广东频道
hain_lines = []  # 地方台-海南频道

other_lines = []  # 其他
other_lines_url = []  # 为降低other文件大小，剔除重复url添加

print("正在读取频道字典...")
# 读取文本
# 主频道
zh_dictionary = read_txt_to_array('主频道/综合频道.txt')
ys_dictionary = read_txt_to_array('主频道/央视频道.txt')
ws_dictionary = read_txt_to_array('主频道/卫视频道.txt')
dy_dictionary = read_txt_to_array('主频道/电影.txt')
gj_dictionary = read_txt_to_array('主频道/国际台.txt')
zb_dictionary = read_txt_to_array('主频道/直播中国.txt')

# 地方台
gd_dictionary = read_txt_to_array('地方台/广东频道.txt')
hain_dictionary = read_txt_to_array('地方台/海南频道.txt')

# 自定义源
urls = read_txt_to_array('assets/urls.txt')
print(f"读取到 {len(urls)} 个URL")
for i, url in enumerate(urls):
    print(f"  {i+1}. {url}")

# 简繁转换
def traditional_to_simplified(text: str) -> str:
    try:
        converter = opencc.OpenCC('t2s')
        simplified_text = converter.convert(text)
        return simplified_text
    except Exception as e:
        print(f"繁简转换错误: {e}")
        return text

# M3U格式判断
def is_m3u_content(text):
    if not text:
        return False
    lines = text.splitlines()
    if not lines:
        return False
    first_line = lines[0].strip()
    return first_line.startswith("#EXTM3U")

def convert_m3u_to_txt(m3u_content):
    # 分行处理
    lines = m3u_content.split('\n')

    # 用于存储结果的列表
    txt_lines = []

    # 临时变量用于存储频道名称
    channel_name = ""

    for line in lines:
        # 过滤掉 #EXTM3U 开头的行
        if line.startswith("#EXTM3U"):
            continue
        # 处理 #EXTINF 开头的行
        if line.startswith("#EXTINF"):
            # 获取频道名称（假设频道名称在引号后）
            channel_name = line.split(',')[-1].strip()
        # 处理 URL 行
        elif line.startswith("http") or line.startswith("rtmp") or line.startswith("p3p"):
            txt_lines.append(f"{channel_name},{line.strip()}")

        # 处理后缀名为m3u，但是内容为txt的文件
        if "#genre#" not in line and "," in line and "://" in line:
            # 定义正则表达式，匹配频道名称,URL 的格式，并确保 URL 包含 "://"
            # xxxx,http://xxxxx.xx.xx
            pattern = r'^[^,]+,[^\s]+://[^\s]+$'
            if bool(re.match(pattern, line)):
                txt_lines.append(line)

    # 将结果合并成一个字符串，以换行符分隔
    return '\n'.join(txt_lines)

# 在list是否已经存在url
def check_url_existence(data_list, url):
    if "127.0.0.1" in url:
        return False
    # Extract URLs from the data list
    urls = [item.split(',')[1] for item in data_list if len(item.split(',')) > 1]
    return url not in urls  # 如果不存在则返回true，需要

# 处理带$的URL
def clean_url(url):
    last_dollar_index = url.rfind('$')
    if last_dollar_index != -1:
        return url[:last_dollar_index]
    return url

# 添加channel_name前剔除部分特定字符
removal_list = ["「IPV4」", "「IPV6」", "[ipv6]", "[ipv4]", "_电信", "电信", "（HD）", "[超清]", "高清", "超清", "-HD", "(HK)", "AKtv", "@", "IPV6", "🎞🎞🎞🎞️", "🎦🎦🎦🎦", " ", "[BD]", "[VGA]", "[HD]", "[SD]", "(1080p)", "(720p)", "(480p)"]

def clean_channel_name(channel_name, removal_list):
    for item in removal_list:
        channel_name = channel_name.replace(item, "")
    # 保留CCTV-格式
    channel_name = channel_name.replace("CCTV0", "CCTV-")
    channel_name = channel_name.replace("PLUS", "+")
    channel_name = channel_name.replace("NewTV-", "NewTV")
    channel_name = channel_name.replace("iHOT-", "iHOT")
    channel_name = channel_name.replace("NEW", "New")
    channel_name = channel_name.replace("New_", "New")
    return channel_name

# 读取纠错频道名称方法
def load_corrections_name(filename):
    corrections = {}
    try:
        with open(filename, 'r', encoding='utf-8-sig') as f:
            for line in f:
                if not line.strip():
                    continue
                parts = line.strip().split(',')
                if len(parts) < 2:
                    continue
                correct_name = parts[0]
                for name in parts[1:]:
                    corrections[name] = correct_name
    except Exception as e:
        print(f"读取纠错文件时出错: {e}")
    return corrections

# 读取纠错文件
corrections_name = load_corrections_name('assets/corrections_name.txt')

def correct_name_data(name):
    if name in corrections_name and name != corrections_name[name]:
        name = corrections_name[name]
    return name

# 检查频道是否已达到最大源数量
def is_channel_full(channel_name, target_list):
    count = sum(1 for line in target_list if line.startswith(channel_name + ","))
    return count >= 10

# 检查URL是否在白名单中
def is_whitelisted_url(url, whitelist):
    for pattern in whitelist:
        if pattern in url:
            return True
    return False

# 检查是否为IPv6地址
def is_ipv6_url(url):
    """检查URL是否包含IPv6地址特征"""
    # IPv6地址特征：包含冒号分隔的十六进制数字，可能包含方括号
    ipv6_patterns = [
        r'\[[0-9a-fA-F:]+:[0-9a-fA-F:]+\]',  # IPv6地址在方括号内
        r'://\[[0-9a-fA-F:]+\]',  # 包含IPv6地址的URL
        r'ipv6',  # 包含ipv6关键字
        r'v6\.',  # 包含v6.子域名
        r':[0-9a-fA-F]{4}:[0-9a-fA-F]{4}:[0-9a-fA-F]{4}:[0-9a-fA-F]{4}',  # IPv6地址模式
        r'240e:',  # 中国电信IPv6地址段
        r'2408:',  # 中国联通IPv6地址段
        r'2409:',  # 中国移动IPv6地址段
    ]
    
    for pattern in ipv6_patterns:
        if re.search(pattern, url, re.IGNORECASE):
            return True
    return False

# 检查是否为RTMP协议
def is_rtmp_url(url):
    """检查URL是否为RTMP协议"""
    return url.startswith('rtmp://')

# 直播源验证函数 - 返回响应时间和是否成功
def validate_stream_url(url, timeout=3):
    """
    验证直播源是否可访问，返回(是否成功, 响应时间)
    """
    try:
        start_time = time.time()
        
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
            return False, None  # TCP连接失败
            
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
                        return False, None
                    
                    # 检查内容类型
                    content_type = response.headers.get('Content-Type', '')
                    if not any(x in content_type for x in ['video', 'audio', 'application/octet-stream', 'application/vnd.apple.mpegurl']):
                        return False, None
                        
            except urllib.error.HTTPError as e:
                # 对于部分HTTP错误，仍然可能是可用的流
                if e.code in [200, 206, 301, 302, 307]:
                    end_time = time.time()
                    return True, end_time - start_time
                return False, None
            except Exception:
                return False, None
                
        end_time = time.time()
        return True, end_time - start_time
        
    except Exception:
        return False, None

# 央视频道名称标准化 - 修改为使用CCTV1格式
def standardize_cctv_name(channel_name):
    """将CCTV频道名称标准化为'CCTV-数字+名称'格式"""
    # CCTV频道名称映射 - 使用CCTV1格式作为键
    cctv_mapping = {
        'CCTV1': 'CCTV-1综合',
        'CCTV2': 'CCTV-2财经',
        'CCTV3': 'CCTV-3综艺',
        'CCTV4': 'CCTV-4中文国际',
        'CCTV5': 'CCTV-5体育',
        'CCTV5+': 'CCTV-5+体育赛事',
        'CCTV6': 'CCTV-6电影',
        'CCTV7': 'CCTV-7国防军事',
        'CCTV8': 'CCTV-8电视剧',
        'CCTV9': 'CCTV-9纪录',
        'CCTV10': 'CCTV-10科教',
        'CCTV11': 'CCTV-11戏曲',
        'CCTV12': 'CCTV-12社会与法',
        'CCTV13': 'CCTV-13新闻',
        'CCTV14': 'CCTV-14少儿',
        'CCTV15': 'CCTV-15音乐',
        'CCTV16': 'CCTV-16奥林匹克',
        'CCTV17': 'CCTV-17农业农村'
    }
    
    # 尝试匹配标准名称
    for short_name, full_name in cctv_mapping.items():
        # 移除频道名称中的横线以便匹配
        clean_name = channel_name.replace('-', '')
        if clean_name.startswith(short_name):
            return full_name
    
    # 如果不是已知的CCTV频道，保持原样
    return channel_name

# 检查URL是否在黑名单中（更严格的检查）
def is_blacklisted_url(url, blacklist):
    """检查URL是否在黑名单中，支持部分匹配"""
    for pattern in blacklist:
        if pattern in url:
            return True
    return False

# 将无效URL添加到黑名单
def add_to_blacklist(url, reason="无效链接"):
    """将URL添加到黑名单文件"""
    try:
        # 检查是否已经在黑名单中
        if url in combined_blacklist:
            return
            
        # 添加到内存中的黑名单
        combined_blacklist.add(url)
        
        # 写入黑名单文件
        with open('assets/whitelist-blacklist/blacklist_auto.txt', 'a', encoding='utf-8') as f:
            f.write(f"{url}  # {reason} - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
        
        print(f"已将无效URL添加到黑名单: {url} - {reason}")
    except Exception as e:
        print(f"添加URL到黑名单时出错: {e}")

# 频道源管理器 - 用于管理每个频道的源并选择最快的10个
class ChannelSourceManager:
    def __init__(self):
        self.sources = {}  # 字典，键为频道名称，值为(响应时间, URL)列表
        self.seen_urls = set()  # 用于跟踪所有已见过的URL，避免重复
        self.lock = threading.Lock()  # 用于线程安全
        
    def add_source(self, channel_name, url):
        # 检查URL是否在黑名单中（使用更严格的检查）
        if is_blacklisted_url(url, combined_blacklist):
            print(f"跳过黑名单URL: {channel_name}, {url}")
            return False
            
        # 检查URL是否为RTMP协议
        if is_rtmp_url(url):
            print(f"跳过RTMP协议URL: {channel_name}, {url}")
            return False
            
        # 检查URL是否已经处理过
        if url in self.seen_urls:
            print(f"跳过重复URL: {channel_name}, {url}")
            return False
            
        self.seen_urls.add(url)
        
        with self.lock:
            if channel_name not in self.sources:
                self.sources[channel_name] = []
            self.sources[channel_name].append((float('inf'), url))  # 初始响应时间为无穷大
        return True
        
    def validate_and_sort_sources(self, max_workers=20):
        """验证所有源并排序，选择每个频道最快的10个有效源"""
        print("开始验证所有源的有效性...")
        
        # 收集所有需要验证的URL
        all_urls = []
        url_to_channel = {}
        
        for channel_name, url_list in self.sources.items():
            for _, url in url_list:
                all_urls.append(url)
                url_to_channel[url] = channel_name
        
        # 使用线程池并行验证URL
        validated_results = {}
        with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
            future_to_url = {executor.submit(validate_stream_url, url): url for url in all_urls}
            for future in concurrent.futures.as_completed(future_to_url):
                url = future_to_url[future]
                try:
                    is_valid, response_time = future.result()
                    validated_results[url] = (is_valid, response_time)
                    if is_valid:
                        print(f"✓ 有效源: {url_to_channel[url]}, {url} (响应时间: {response_time:.2f}s)")
                    else:
                        print(f"✗ 无效源: {url_to_channel[url]}, {url}")
                        # 将无效URL添加到黑名单
                        add_to_blacklist(url, "验证失败")
                except Exception as e:
                    print(f"验证URL时发生错误 {url}: {e}")
                    validated_results[url] = (False, None)
                    # 将错误URL添加到黑名单
                    add_to_blacklist(url, f"验证错误: {e}")
        
        # 更新每个频道的源列表
        for channel_name in list(self.sources.keys()):
            valid_sources = []
            for response_time, url in self.sources[channel_name]:
                if url in validated_results:
                    is_valid, actual_response_time = validated_results[url]
                    if is_valid and actual_response_time is not None:
                        valid_sources.append((actual_response_time, url))
            
            # 按响应时间排序并选择最快的10个
            valid_sources.sort(key=lambda x: x[0])
            self.sources[channel_name] = valid_sources[:10]
            
            print(f"频道 {channel_name}: 找到 {len(valid_sources)} 个有效源，保留 {len(self.sources[channel_name])} 个最快源")
    
    def get_sorted_lines(self, channel_dictionary):
        """获取排序后的频道行"""
        result = []
        for channel_name in channel_dictionary:
            if channel_name in self.sources:
                for response_time, url in self.sources[channel_name]:
                    result.append(f"{channel_name},{url}")
        return result

# 创建全局的频道源管理器
source_manager = ChannelSourceManager()

# 分发直播源
def process_channel_line(line):
    try:
        if "#genre#" not in line and "#EXTINF:" not in line and "," in line and "://" in line:
            parts = line.split(',', 1)
            if len(parts) < 2:
                return
                
            channel_name = parts[0]
            channel_name = traditional_to_simplified(channel_name)
            channel_name = clean_channel_name(channel_name, removal_list)
            channel_name = correct_name_data(channel_name).strip()

            # 对央视频道进行标准化处理
            if channel_name.startswith('CCTV'):
                channel_name = standardize_cctv_name(channel_name)

            channel_address = clean_url(parts[1]).strip()

            # 检查是否为IPv6地址，如果是则跳过
            if is_ipv6_url(channel_address):
                print(f"跳过IPv6源: {channel_name}, {channel_address}")
                return

            # 检查是否在白名单中
            is_whitelisted = is_whitelisted_url(channel_address, whitelist)
            
            # 特别处理直播中国分类 - 只保留明确的直播中国频道
            if channel_name in zb_dictionary:
                if is_whitelisted or not is_channel_full(channel_name, zb_lines):
                    if source_manager.add_source(channel_name, channel_address):
                        print(f"添加到直播中国: {channel_name}, {channel_address}")
            # 新增综合频道处理（放在央视频道前面）
            elif channel_name in zh_dictionary:
                if is_whitelisted or not is_channel_full(channel_name, zh_lines):
                    if source_manager.add_source(channel_name, channel_address):
                        print(f"添加到综合频道: {channel_name}, {channel_address}")
            elif channel_name in ys_dictionary:
                # 对央视频道放宽验证条件
                if is_whitelisted or not is_channel_full(channel_name, ys_lines):
                    if source_manager.add_source(channel_name, channel_address):
                        print(f"添加到央视频道: {channel_name}, {channel_address}")
            elif channel_name in ws_dictionary:
                # 对卫视频道放宽验证条件
                if is_whitelisted or not is_channel_full(channel_name, ws_lines):
                    if source_manager.add_source(channel_name, channel_address):
                        print(f"添加到卫视频道: {channel_name}, {channel_address}")
            elif channel_name in dy_dictionary:
                if is_whitelisted or not is_channel_full(channel_name, dy_lines):
                    if source_manager.add_source(channel_name, channel_address):
                        print(f"添加到电影频道: {channel_name}, {channel_address}")
            elif channel_name in gj_dictionary:
                if is_whitelisted or not is_channel_full(channel_name, gj_lines):
                    if source_manager.add_source(channel_name, channel_address):
                        print(f"添加到国际台: {channel_name}, {channel_address}")
            elif channel_name in gd_dictionary:
                if is_whitelisted or not is_channel_full(channel_name, gd_lines):
                    if source_manager.add_source(channel_name, channel_address):
                        print(f"添加到广东频道: {channel_name}, {channel_address}")
            elif channel_name in hain_dictionary:
                if is_whitelisted or not is_channel_full(channel_name, hain_lines):
                    if source_manager.add_source(channel_name, channel_address):
                        print(f"添加到海南频道: {channel_name}, {channel_address}")
            else:
                print(f"未分类频道: {channel_name}, {channel_address}")
    except Exception as e:
        print(f"处理频道行时出错: {e}, 行内容: {line}")

# 修复URL处理函数
def safe_process_url(url):
    try:
        # 对URL进行编码处理
        encoded_url = quote(url, safe=':/?&=')
        process_url(encoded_url)
    except Exception as e:
        print(f"处理URL时发生错误：{e}")

def process_url(url):
    print(f"\n开始处理URL: {url}")
    try:
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
        }
        req = urllib.request.Request(url, headers=headers)
        # 修改超时时间为10秒
        with urllib.request.urlopen(req, timeout=10) as response:
            data = response.read()
            try:
                text = data.decode('utf-8')
            except UnicodeDecodeError:
                try:
                    text = data.decode('gbk')
                except UnicodeDecodeError:
                    try:
                        text = data.decode('iso-8859-1')
                    except UnicodeDecodeError:
                        print("无法确定合适的编码格式进行解码。")
                        return

            if is_m3u_content(text):
                text = convert_m3u_to_txt(text)

            lines = text.split('\n')
            print(f"原始行数: {len(lines)}")
            valid_lines = 0
            for line in lines:
                if "#genre#" not in line and "," in line and "://" in line:
                    parts = line.split(',', 1)
                    if len(parts) < 2:
                        continue
                        
                    channel_name, channel_address = parts
                    if "#" not in channel_address:
                        process_channel_line(line)
                        valid_lines += 1
                    else:
                        url_list = channel_address.split('#')
                        for channel_url in url_list:
                            if "://" in channel_url:
                                newline = f'{channel_name},{channel_url}'
                                process_channel_line(newline)
                                valid_lines += 1

            print(f"有效行数: {valid_lines}")

    except Exception as e:
        print(f"处理URL时发生错误：{e}")

def sort_data(order, data):
    order_dict = {name: i for i, name in enumerate(order)}

    def sort_key(line):
        name = line.split(',')[0]
        return order_dict.get(name, len(order))

    sorted_data = sorted(data, key=sort_key)
    return sorted_data

# 加入配置的url
print("\n开始处理所有URL...")
for url in urls:
    if url.startswith("http"):
        safe_process_url(url)

# 验证所有源并选择最快的10个
source_manager.validate_and_sort_sources()

# 获取处理后的频道源
zh_lines = source_manager.get_sorted_lines(zh_dictionary)
ys_lines = source_manager.get_sorted_lines(ys_dictionary)
ws_lines = source_manager.get_sorted_lines(ws_dictionary)
dy_lines = source_manager.get_sorted_lines(dy_dictionary)
gj_lines = source_manager.get_sorted_lines(gj_dictionary)
zb_lines = source_manager.get_sorted_lines(zb_dictionary)
gd_lines = source_manager.get_sorted_lines(gd_dictionary)
hain_lines = source_manager.get_sorted_lines(hain_dictionary)

# 获取当前的 UTC 时间
utc_time = datetime.now(timezone.utc)
beijing_time = utc_time + timedelta(hours=8)
formatted_time = beijing_time.strftime("%Y%m%d %H:%M")
# 修改链接指向新文件名
version = formatted_time + ",https://www.cloudplains.cn/tv202303.txt"

# 打印统计信息
print(f"\n统计信息:")
print(f"综合频道: {len(zh_lines)} 行")
print(f"央视频道: {len(ys_lines)} 行")
print(f"卫视频道: {len(ws_lines)} 行")
print(f"电影频道: {len(dy_lines)} 行")
print(f"国际台: {len(gj_lines)} 行")
print(f"直播中国: {len(zb_lines)} 行")
print(f"广东频道: {len(gd_lines)} 行")
print(f"海南频道: {len(hain_lines)} 行")

# 合并所有对象中的行文本（已移除IPV6频道和港澳台频道）
all_lines = (["更新时间,#genre#"] + [version] + ['\n'] +
           ["综合频道,#genre#"] + sort_data(zh_dictionary, zh_lines) + ['\n'] +
           ["央视频道,#genre#"] + sort_data(ys_dictionary, ys_lines) + ['\n'] +
           ["卫视频道,#genre#"] + sort_data(ws_dictionary, ws_lines) + ['\n'] +
           ["国际台,#genre#"] + sort_data(gj_dictionary, gj_lines) + ['\n'] +
           ["广东频道,#genre#"] + sort_data(gd_dictionary, gd_lines) + ['\n'] +
           ["海南频道,#genre#"] + sort_data(hain_dictionary, hain_lines) + ['\n'] +
           ["电影频道,#genre#"] + sort_data(dy_dictionary, dy_lines) + ['\n'] +
           ["直播中国,#genre#"] + sort_data(zb_dictionary, zb_lines) + ['\n'])

# 修改输出文件名为 tv202303.txt
output_file = "tv202303.txt"

try:
    with open(output_file, 'w', encoding='utf-8') as f:
        for line in all_lines:
            f.write(line + '\n')
    print(f"合并后的文本已保存到文件: {output_file}")

except Exception as e:
    print(f"保存文件时发生错误：{e}")

def make_m3u(txt_file, m3u_file):
    try:
        output_text = '#EXTM3U x-tvg-url="https://epg.112114.xyz/pp.xml.gz"\n'
        with open(txt_file, "r", encoding='utf-8') as file:
            input_text = file.read()

        lines = input_text.strip().split("\n")
        group_name = ""
        for line in lines:
            parts = line.split(",")
            if len(parts) == 2 and "#genre#" in line:
                group_name = parts[0]
            elif len(parts) == 2:
                channel_name = parts[0]
                channel_url = parts[1]
                logo_url = "https://epg.112114.xyz/logo/"+channel_name+".png"
                output_text += f"#EXTINF:-1 tvg-name=\"{channel_name}\" tvg-logo=\"{logo_url}\" group-title=\"{group_name}\",{channel_name}\n"
                output_text += f"{channel_url}\n"

        with open(f"{m3u_file}", "w", encoding='utf-8') as file:
            file.write(output_text)
        print(f"M3U文件 '{m3u_file}' 生成成功。")
    except Exception as e:
        print(f"生成M3U文件时发生错误: {e}")

# 修改M3U文件名为 tv202303.m3u
make_m3u(output_file, "tv202303.m3u")

# 执行结束时间
timeend = datetime.now()
elapsed_time = timeend - timestart
total_seconds = elapsed_time.total_seconds()
minutes = int(total_seconds // 60)
seconds = int(total_seconds % 60)

print(f"执行时间: {minutes} 分 {seconds} 秒")
print(f"blacklist行数: {len(combined_blacklist)}")
print(f"{output_file}行数: {len(all_lines)}")