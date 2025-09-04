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
        with open(file_name, 'r', encoding='utf-8-sig') as file:  # 使用utf-8-sig自动处理BOM
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
    try:
        # 先尝试 UTF-8 编码
        with open(file_path, 'r', encoding='utf-8-sig') as file:  # 使用utf-8-sig自动处理BOM
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

    BlackList = [line.split(',')[1].strip() for line in lines if ',' in line]
    return BlackList

print("正在读取黑名单...")
blacklist_auto = read_blacklist_from_txt('assets/whitelist-blacklist/blacklist_auto.txt')
black_list_manual = read_blacklist_from_txt('assets/whitelist-blacklist/blacklist_manual.txt')  # 文件名已更正
combined_blacklist = set(blacklist_auto + black_list_manual)
print(f"合并黑名单行数: {len(combined_blacklist)}")

# 定义多个对象用于存储不同内容的行文本
zh_lines = []  # 综合频道
ys_lines = []  # 央视频道
ws_lines = []  # 卫视频道
dy_lines = []  # 电影频道
gat_lines = []  # 港澳台
gj_lines = []  # 国际台
zb_lines = []  # 直播中国
gd_lines = []  # 地方台-广东频道
hain_lines = []  # 地方台-海南频道
ipv6_lines = []  # IPV6频道 - 新增

other_lines = []  # 其他
other_lines_url = []  # 为降低other文件大小，剔除重复url添加

print("正在读取频道字典...")
# 读取文本
# 主频道
zh_dictionary = read_txt_to_array('主频道/综合频道.txt')  # 新增综合频道
ys_dictionary = read_txt_to_array('主频道/央视频道.txt')
ws_dictionary = read_txt_to_array('主频道/卫视频道.txt')
dy_dictionary = read_txt_to_array('主频道/电影.txt')
gat_dictionary = read_txt_to_array('主频道/港澳台.txt')
gj_dictionary = read_txt_to_array('主频道/国际台.txt')
zb_dictionary = read_txt_to_array('主频道/直播中国.txt')

# 地方台
gd_dictionary = read_txt_to_array('地方台/广东频道.txt')
hain_dictionary = read_txt_to_array('地方台/海南频道.txt')

# 自定义源
urls = read_txt_to_array('assets/urls.txt')
print(f"读取到 {len(urls)} 个URL")

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
    channel_name = channel_name.replace("CCTV-", "CCTV")
    channel_name = channel_name.replace("CCTV0", "CCTV")
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
        with open(filename, 'r', encoding='utf-8-sig') as f:  # 使用utf-8-sig自动处理BOM
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

# 检查是否为IPv6地址
def is_ipv6_url(url):
    """检查URL是否包含IPv6地址特征"""
    # IPv6地址特征：包含冒号分隔的十六进制数字，可能包含方括号
    ipv6_patterns = [
        r'\[[0-9a-fA-F:]+:[0-9a-fA-F:]+\]',  # IPv6地址在方括号内
        r'://\[[0-9a-fA-F:]+\]',  # 包含IPv6地址的URL
        r'ipv6',  # 包含ipv6关键字
        r'v6\.',  # 包含v6.子域名
    ]
    
    for pattern in ipv6_patterns:
        if re.search(pattern, url, re.IGNORECASE):
            return True
    return False

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

            channel_address = clean_url(parts[1]).strip()
            line = channel_name + "," + channel_address

            if len(channel_address) > 0 and channel_address not in combined_blacklist:
                # 特别处理直播中国分类 - 只保留明确的直播中国频道
                if channel_name in zb_dictionary:
                    if check_url_existence(zb_lines, channel_address) and not is_channel_full(channel_name, zb_lines):
                        zb_lines.append(line)
                # 新增综合频道处理（放在央视频道前面）
                elif channel_name in zh_dictionary:
                    if check_url_existence(zh_lines, channel_address) and not is_channel_full(channel_name, zh_lines):
                        zh_lines.append(line)
                elif channel_name in ys_dictionary:
                    # 对央视频道进行额外验证
                    if (check_url_existence(ys_lines, channel_address) and not is_channel_full(channel_name, ys_lines) and
                        validate_stream_url(channel_address)):
                        ys_lines.append(line)
                        # 如果是IPv6源，也添加到IPv6频道
                        if is_ipv6_url(channel_address) and check_url_existence(ipv6_lines, channel_address) and not is_channel_full(channel_name, ipv6_lines):
                            ipv6_lines.append(line)
                    else:
                        print(f"央视频道验证失败: {channel_name} - {channel_address}")
                elif channel_name in ws_dictionary:
                    # 对卫视频道进行额外验证
                    if (check_url_existence(ws_lines, channel_address) and not is_channel_full(channel_name, ws_lines) and
                        validate_stream_url(channel_address)):
                        ws_lines.append(line)
                        # 如果是IPv6源，也添加到IPv6频道
                        if is_ipv6_url(channel_address) and check_url_existence(ipv6_lines, channel_address) and not is_channel_full(channel_name, ipv6_lines):
                            ipv6_lines.append(line)
                    else:
                        print(f"卫视频道验证失败: {channel_name} - {channel_address}")
                elif channel_name in dy_dictionary:
                    if check_url_existence(dy_lines, channel_address) and not is_channel_full(channel_name, dy_lines):
                        dy_lines.append(line)
                elif channel_name in gat_dictionary:
                    if check_url_existence(gat_lines, channel_address) and not is_channel_full(channel_name, gat_lines):
                        gat_lines.append(line)
                elif channel_name in gj_dictionary:
                    if check_url_existence(gj_lines, channel_address) and not is_channel_full(channel_name, gj_lines):
                        gj_lines.append(line)
                elif channel_name in gd_dictionary:
                    if check_url_existence(gd_lines, channel_address) and not is_channel_full(channel_name, gd_lines):
                        gd_lines.append(line)
                elif channel_name in hain_dictionary:
                    if check_url_existence(hain_lines, channel_address) and not is_channel_full(channel_name, hain_lines):
                        hain_lines.append(line)
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
        # 修改超时时间为5秒
        with urllib.request.urlopen(req, timeout=5) as response:
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
            # 注释掉这行，不再向other_lines添加换行符
            # other_lines.append('\n')

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
print(f"港澳台: {len(gat_lines)} 行")
print(f"国际台: {len(gj_lines)} 行")
print(f"直播中国: {len(zb_lines)} 行")
print(f"广东频道: {len(gd_lines)} 行")
print(f"海南频道: {len(hain_lines)} 行")
print(f"IPV6频道: {len(ipv6_lines)} 行")  # 新增统计

# 合并所有对象中的行文本（已移除other_lines）
all_lines = ["更新时间,#genre#"] + [version] + ['\n'] + \
           ["综合频道,#genre#"] + sort_data(zh_dictionary, zh_lines) + ['\n'] + \
           ["央视频道,#genre#"] + sort_data(ys_dictionary, ys_lines) + ['\n'] + \
           ["卫视频道,#genre#"] + sort_data(ws_dictionary, ws_lines) + ['\n'] + \
           ["IPV6频道,#genre#"] + sort_data(ys_dictionary + ws_dictionary, ipv6_lines) + ['\n'] + \
           ["港澳台,#genre#"] + sort_data(gat_dictionary, gat_lines) + ['\n'] + \
           ["国际台,#genre#"] + sort_data(gj_dictionary, gj_lines) + ['\n'] + \
           ["广东频道,#genre#"] + sort_data(gd_dictionary, gd_lines) + ['\n'] + \
           ["海南频道,#genre#"] + sort_data(hain_dictionary, hain_lines) + ['\n'] + \
           ["电影频道,#genre#"] + sort_data(dy_dictionary, dy_lines) + ['\n'] + \
           ["直播中国,#genre#"] + sort_data(zb_dictionary, zb_lines) + ['\n']

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
print(f"{output_file}行数: {len(all_lines)}")  # 修复这里的打印错误