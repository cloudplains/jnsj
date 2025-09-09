import urllib.request
from urllib.parse import urlparse, quote
import re
import os
from datetime import datetime, timedelta, timezone
import socket
import ssl
import argparse
import concurrent.futures
import time
import json

# 跳过SSL证书验证
ssl._create_default_https_context = ssl._create_unverified_context

# 分类规则 - 根据频道名称关键词分类
def categorize_channel(channel_name):
    channel_name_lower = channel_name.lower()
    
    # 央视分类 - 只保留CCTV和央视开头的
    if channel_name_lower.startswith(('cctv', '央视')):
        return "央视频道"
    
    # 卫视分类 - 只保留明确带有"卫视"字样的
    elif '卫视' in channel_name and not any(keyword in channel_name for keyword in ['广东', '海南', '广州', '深圳', '海口', '三亚']):
        return "卫视频道"
    
    # 广东频道 - 只保留广东地市名，且不能是卫视
    elif any(city in channel_name for city in 
             ['广东', '广州', '深圳', '珠海', '汕头', '佛山', '韶关', '湛江', 
              '肇庆', '江门', '茂名', '惠州', '梅州', '汕尾', '河源', '阳江', 
              '清远', '东莞', '中山', '潮州', '揭阳', '云浮']):
        # 确保不是卫视
        if '卫视' not in channel_name:
            return "广东频道"
        else:
            return "卫视频道"
    
    # 海南频道 - 只保留海南地市名，且不能是卫视
    elif any(city in channel_name for city in 
             ['海南', '海口', '三亚', '三沙', '儋州', '琼海', '文昌', '万宁', 
              '东方', '五指山', '乐东', '澄迈', '临高', '定安', '屯昌', '陵水']):
        # 确保不是卫视
        if '卫视' not in channel_name:
            return "海南频道"
        else:
            return "卫视频道"
    
    # 电影分类
    elif any(movie_keyword in channel_name_lower for movie_keyword in 
             ['电影', '影院', '影视频道', 'movie', 'cinema']):
        return "电影频道"
    
    # 国际分类
    elif any(international_keyword in channel_name_lower for international_keyword in 
             ['凤凰', '翡翠', '明珠', 'hbo', 'discovery', 'bbc', 'cnn', 'nhk', 'tvb']):
        return "国际频道"
    
    # 默认不保留
    else:
        return None

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

# 简化的直播源验证函数（只检查TCP连接）
def validate_stream_url(url, timeout=2):
    """
    简化验证直播源是否可访问，只检查TCP连接
    """
    # 跳过MP4后缀的URL
    if url.lower().endswith('.mp4'):
        return False
        
    try:
        # 解析URL获取主机和端口
        parsed_url = urlparse(url)
        host = parsed_url.hostname
        if not host:
            return False
            
        port = parsed_url.port or (443 if parsed_url.scheme == 'https' else 80)
        
        # 尝试TCP连接测试
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(timeout)
        result = sock.connect_ex((host, port))
        sock.close()
        
        return result == 0  # 返回连接是否成功
        
    except Exception:
        return False

# 处理单行直播源
def process_line(line, timeout):
    # 跳过空行和注释行
    if not line.strip() or line.startswith('#') or 'genre' in line.lower():
        return None
        
    # 检查是否为标准格式（频道名称,URL）
    if ',' in line and '://' in line:
        parts = line.split(',', 1)
        channel_name = parts[0].strip()
        url = parts[1].strip()
        
        # 跳过MP4后缀的URL
        if url.lower().endswith('.mp4'):
            print(f"跳过MP4源: {channel_name} - {url}")
            return None
            
        # 跳过体育分类
        if any(sports_keyword in channel_name.lower() for sports_keyword in 
              ['体育', 'sports', '足球', '篮球', '网球', '乒乓球']):
            print(f"跳过体育频道: {channel_name} - {url}")
            return None
            
        # 验证URL有效性
        if validate_stream_url(url, timeout):
            category = categorize_channel(channel_name)
            
            if category:
                return {"category": category, "channel": channel_name, "url": url}
            else:
                print(f"跳过杂源: {channel_name} - {url}")
                return None
        else:
            print(f"无效: {channel_name} - {url}")
            return None
    else:
        # 不属于节目源的行直接去掉
        print(f"移除非节目源行: {line}")
        return None

# 处理直播源文件
def process_live_file(input_file, output_file, progress_file, timeout=2, workers=5, max_time=300):
    print(f"开始处理直播源文件: {input_file}")
    
    # 读取进度文件
    progress = {}
    if os.path.exists(progress_file):
        try:
            with open(progress_file, 'r', encoding='utf-8') as f:
                progress = json.load(f)
        except Exception as e:
            print(f"读取进度文件时出错: {e}")
    
    # 读取原始文件
    lines = read_txt_to_array(input_file)
    if not lines:
        print("文件为空或读取失败")
        return
    
    # 获取当前的 UTC 时间
    utc_time = datetime.now(timezone.utc)
    beijing_time = utc_time + timedelta(hours=8)
    formatted_time = beijing_time.strftime("%Y-%m-%d %H:%M")
    
    # 确定开始处理的索引
    last_processed_index = progress.get('last_processed_index', 0)
    print(f"从索引 {last_processed_index} 开始处理，总行数: {len(lines)}")
    
    # 记录开始时间
    start_time = time.time()
    
    # 使用多线程处理
    results = []
    with concurrent.futures.ThreadPoolExecutor(max_workers=workers) as executor:
        # 提交任务
        future_to_index = {}
        for i in range(last_processed_index, len(lines)):
            # 检查是否超时
            if time.time() - start_time > max_time * 60:  # max_time是分钟，转换为秒
                print(f"达到最大运行时间 {max_time} 分钟，停止处理")
                break
                
            future = executor.submit(process_line, lines[i], timeout)
            future_to_index[future] = i
            
        # 处理完成的任务
        for future in concurrent.futures.as_completed(future_to_index):
            try:
                result = future.result()
                if result:
                    results.append(result)
            except Exception as exc:
                index = future_to_index[future]
                print(f"处理行时发生异常: {lines[index]}, 错误: {exc}")
    
    # 更新最后处理的索引
    last_processed_index = min(len(lines), future_to_index[future] + 1 if future_to_index else last_processed_index)
    progress['last_processed_index'] = last_processed_index
    progress['last_processed_time'] = formatted_time
    
    # 按分类组织结果
    categorized_results = {}
    for result in results:
        category = result["category"]
        if category not in categorized_results:
            categorized_results[category] = []
        categorized_results[category].append(f"{result['channel']},{result['url']}")
    
    # 读取现有的有效源（如果有）
    existing_categories = {}
    if os.path.exists(output_file):
        current_category = None
        with open(output_file, 'r', encoding='utf-8') as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                if line.endswith(',#genre#'):
                    current_category = line.replace(',#genre#', '')
                    existing_categories[current_category] = []
                elif current_category and ',' in line and '://' in line:
                    existing_categories[current_category].append(line)
    
    # 合并现有结果和新结果
    for category, channels in categorized_results.items():
        if category not in existing_categories:
            existing_categories[category] = []
        
        # 去重
        existing_urls = {line.split(',')[1] for line in existing_categories[category]}
        for channel in channels:
            url = channel.split(',')[1]
            if url not in existing_urls:
                existing_categories[category].append(channel)
                existing_urls.add(url)
    
    # 写入新文件
    try:
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write(f"# 更新时间: {formatted_time}\n\n")
            
            # 按固定顺序写入分类
            categories_order = ["央视频道", "卫视频道", "电影频道", "国际频道", "广东频道", "海南频道"]
            
            for category in categories_order:
                if category in existing_categories and existing_categories[category]:
                    f.write(f"{category},#genre#\n")
                    for channel in sorted(existing_categories[category]):
                        f.write(f"{channel}\n")
                    f.write("\n")
        
        print(f"已保存分类直播源到: {output_file}")
        print(f"原始行数: {len(lines)}, 已处理行数: {last_processed_index}, 有效频道数: {len(results)}")
        
        # 打印各分类统计
        print("\n各分类统计:")
        for category in categories_order:
            if category in existing_categories:
                count = len(existing_categories[category])
                print(f"{category}: {count} 个频道")
                
    except Exception as e:
        print(f"保存文件时发生错误：{e}")
    
    # 保存进度
    try:
        with open(progress_file, 'w', encoding='utf-8') as f:
            json.dump(progress, f, ensure_ascii=False, indent=2)
        print(f"已保存进度到: {progress_file}")
    except Exception as e:
        print(f"保存进度文件时发生错误：{e}")
    
    # 检查是否处理完成
    if last_processed_index >= len(lines):
        print("所有直播源已处理完成，下次运行将从头开始")
        # 重置进度
        progress['last_processed_index'] = 0
        with open(progress_file, 'w', encoding='utf-8') as f:
            json.dump(progress, f, ensure_ascii=False, indent=2)

# 主函数
if __name__ == "__main__":
    # 解析命令行参数
    parser = argparse.ArgumentParser(description='验证直播源有效性')
    parser.add_argument('--timeout', type=float, default=2, help='验证超时时间（秒）')
    parser.add_argument('--workers', type=int, default=5, help='并发工作线程数')
    parser.add_argument('--max-time', type=int, default=300, help='最大运行时间（分钟）')
    args = parser.parse_args()
    
    # 执行开始时间
    timestart = datetime.now()
    
    # 输入和输出文件
    input_file = "assets/live.txt"
    output_file = "assets/live.txt"  # 覆盖原文件
    progress_file = "progress.json"  # 进度文件
    
    # 处理直播源文件
    process_live_file(input_file, output_file, progress_file, args.timeout, args.workers, args.max_time)
    
    # 执行结束时间
    timeend = datetime.now()
    elapsed_time = timeend - timestart
    total_seconds = elapsed_time.total_seconds()
    minutes = int(total_seconds // 60)
    seconds = int(total_seconds % 60)
    
    print(f"执行时间: {minutes} 分 {seconds} 秒")