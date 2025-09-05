import asyncio
import aiohttp
import re
import datetime
import requests
import eventlet
import os
import time
import threading
import tempfile
import json
from queue import Queue

# 设置事件监听补丁
eventlet.monkey_patch()

# 原始URL列表（示例，实际使用时请替换）
urls = [
    "http://example.com:8080",
    "http://another-example.com:80"
    # ... 实际URL列表 ...
]

async def modify_urls(url):
    """生成修改后的URL列表"""
    modified_urls = []
    # 确保URL格式正确
    if "//" not in url or ":" not in url:
        return modified_urls
        
    ip_start_index = url.find("//") + 2
    ip_end_index = url.find(":", ip_start_index)
    
    # 检查索引有效性
    if ip_end_index == -1 or ip_start_index >= len(url):
        return modified_urls
        
    base_url = url[:ip_start_index]
    ip_address = url[ip_start_index:ip_end_index]
    port = url[ip_end_index:]
    ip_end = "/iptv/live/1000.json?key=txiptv"
    
    # 仅当IP地址格式正确时处理
    if ip_address.count(".") == 3:
        base_ip = ip_address.rsplit(".", 1)[0] + "."
        for i in range(1, 256):
            modified_ip = f"{base_ip}{i}"
            modified_url = f"{base_url}{modified_ip}{port}{ip_end}"
            modified_urls.append(modified_url)
            
    return modified_urls

async def is_url_accessible(session, url, semaphore):
    """检查URL是否可访问"""
    async with semaphore:
        try:
            async with session.get(url, timeout=2) as response:  # 增加超时时间
                if response.status == 200:
                    current_time = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                    print(f"{current_time} 可用源: {url}")
                    return url
        except (aiohttp.ClientError, asyncio.TimeoutError):
            pass
        return None

async def check_urls(session, urls, semaphore):
    """批量检查URL可用性"""
    tasks = []
    for url in urls:
        url = url.strip()
        modified_urls = await modify_urls(url)
        for modified_url in modified_urls:
            task = asyncio.create_task(is_url_accessible(session, modified_url, semaphore))
            tasks.append(task)
    results = await asyncio.gather(*tasks)
    valid_urls = [result for result in results if result]
    return valid_urls

async def fetch_json(session, url, semaphore):
    """获取并处理JSON数据"""
    async with semaphore:
        try:
            # 解析URL组件
            ip_start_index = url.find("//") + 2
            ip_dot_start = url.find(".") + 1
            ip_index_second = url.find("/", ip_dot_start)
            
            if ip_index_second == -1:
                return []
                
            base_url = url[:ip_start_index]
            ip_address = url[ip_start_index:ip_index_second]
            url_x = f"{base_url}{ip_address}"

            # 获取JSON数据
            async with session.get(url, timeout=2) as response:  # 增加超时时间
                try:
                    json_data = await response.json()
                except json.JSONDecodeError:
                    print(f"JSON解析失败: {url}")
                    return []
                    
                results = []
                try:
                    for item in json_data.get('data', []):
                        if isinstance(item, dict):
                            name = item.get('name', '')
                            urlx = item.get('url', '')
                            
                            if ',' in urlx:
                                continue
                                
                            if 'http' in urlx:
                                urld = f"{urlx}"
                            else:
                                urld = f"{url_x}{urlx}"

                            if name and urlx:
                                # 频道名称标准化处理
                                name = name.replace("cctv", "CCTV").replace("中央", "CCTV").replace("央视", "CCTV")
                                name = re.sub(r"高清|超高|HD|标清|频道|-| |PLUS|＋|\(|\)", "", name)
                                name = re.sub(r"CCTV(\d+)台", r"CCTV\1", name)
                                
                                # CCTV频道标准化
                                cctv_mappings = {
                                    "CCTV1综合": "CCTV1", "CCTV2财经": "CCTV2",
                                    "CCTV3综艺": "CCTV3", "CCTV4国际": "CCTV4",
                                    "CCTV4中文国际": "CCTV4", "CCTV4欧洲": "CCTV4",
                                    "CCTV5体育": "CCTV5", "CCTV6电影": "CCTV6",
                                    "CCTV7军事": "CCTV7", "CCTV7军农": "CCTV7",
                                    "CCTV7农业": "CCTV7", "CCTV7国防军事": "CCTV7",
                                    "CCTV8电视剧": "CCTV8", "CCTV9记录": "CCTV9",
                                    "CCTV9纪录": "CCTV9", "CCTV10科教": "CCTV10",
                                    "CCTV11戏曲": "CCTV11", "CCTV12社会与法": "CCTV12",
                                    "CCTV13新闻": "CCTV13", "CCTV新闻": "CCTV13",
                                    "CCTV14少儿": "CCTV14", "CCTV15音乐": "CCTV15",
                                    "CCTV16奥林匹克": "CCTV16", "CCTV17农业农村": "CCTV17",
                                    "CCTV17农业": "CCTV17", "CCTV5+体育赛视": "CCTV5+",
                                    "CCTV5+体育赛事": "CCTV5+", "CCTV5+体育": "CCTV5+"
                                }
                                name = cctv_mappings.get(name, name)
                                
                                results.append(f"{name},{urld}")
                except Exception as e:
                    print(f"处理JSON数据时出错: {str(e)}")
                return results
        except (aiohttp.ClientError, asyncio.TimeoutError) as e:
            print(f"请求失败: {url} - {str(e)}")
            return []
        return []

async def main():
    """主处理函数"""
    print(f"[{datetime.datetime.now()}] 开始处理任务")
    
    # 准备基础URL
    x_urls = []
    for url in urls:
        url = url.strip()
        ip_start_index = url.find("//") + 2
        ip_end_index = url.find(":", ip_start_index)
        
        if ip_end_index == -1:
            continue
            
        ip_dot_start = url.find(".") + 1
        ip_dot_second = url.find(".", ip_dot_start) + 1
        ip_dot_three = url.find(".", ip_dot_second) + 1
        
        if -1 in [ip_dot_start, ip_dot_second, ip_dot_three]:
            continue
            
        base_url = url[:ip_start_index]
        ip_address = url[ip_start_index:ip_dot_three]
        port = url[ip_end_index:]
        ip_end = "1"
        modified_ip = f"{ip_address}{ip_end}"
        x_url = f"{base_url}{modified_ip}{port}"
        x_urls.append(x_url)
        
    unique_urls = set(x_urls)
    print(f"[{datetime.datetime.now()}] 发现 {len(unique_urls)} 个基础源")

    # 检查URL可用性
    semaphore = asyncio.Semaphore(100)  # 降低并发量
    async with aiohttp.ClientSession() as session:
        print(f"[{datetime.datetime.now()}] 开始检查URL可用性")
        valid_urls = await check_urls(session, unique_urls, semaphore)
        print(f"[{datetime.datetime.now()}] 发现 {len(valid_urls)} 个可用源")
        
        # 获取频道数据
        all_results = []
        tasks = []
        for url in valid_urls:
            task = asyncio.create_task(fetch_json(session, url, semaphore))
            tasks.append(task)
            
        results = await asyncio.gather(*tasks)
        for sublist in results:
            all_results.extend(sublist)
            
    print(f"[{datetime.datetime.now()}] 共获取 {len(all_results)} 个频道")

    # 频道测速处理
    task_queue = Queue()
    results = []
    error_channels = []

    def worker():
        """测速工作线程"""
        while True:
            try:
                # 设置30秒超时获取任务
                channel_name, channel_url = task_queue.get(timeout=30)
            except:
                break
                
            try:
                # 获取M3U8内容
                channel_url_t = channel_url.rstrip(channel_url.split('/')[-1])
                response = requests.get(channel_url, timeout=3)
                response.raise_for_status()
                lines = response.text.strip().split('\n')
                
                # 处理TS列表
                ts_lists = [line.split('/')[-1] for line in lines if not line.startswith('#')]
                if not ts_lists:
                    raise ValueError("未找到TS文件列表")
                    
                ts_lists_0 = ts_lists[0].split('?')[0]  # 清除参数
                ts_url = channel_url_t + ts_lists[0]  # 完整的TS文件URL
                
                # 使用临时文件处理
                with tempfile.NamedTemporaryFile(delete=True) as temp_file:
                    # 限时下载测试
                    start_time = time.time()
                    try:
                        with eventlet.Timeout(5, False):
                            ts_response = requests.get(ts_url, timeout=3)
                            ts_response.raise_for_status()
                            content = ts_response.content
                            temp_file.write(content)
                            temp_file.flush()
                            
                            end_time = time.time()
                            response_time = max(end_time - start_time, 0.001)  # 防止除零
                            
                            # 计算下载速度
                            file_size = len(content)
                            download_speed = file_size / response_time / 1024 / 1024  # MB/s
                            normalized_speed = min(max(download_speed, 0.001), 100)
                            
                            result = channel_name, channel_url, f"{normalized_speed:.3f} MB/s"
                            results.append(result)
                            
                    except eventlet.Timeout:
                        print(f"测速超时: {channel_name}")
                        raise
            except Exception as e:
                error_channel = channel_name, channel_url
                error_channels.append(error_channel)
                
            # 更新进度
            total = len(all_results)
            processed = len(results) + len(error_channels)
            progress = (processed / total) * 100 if total > 0 else 0
            current_time = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            print(f"{current_time} 可用: {len(results)} 不可用: {len(error_channels)} 进度: {progress:.2f}%")
            
            # 标记任务完成
            task_queue.task_done()

    def channel_key(channel_name):
        """频道排序辅助函数"""
        match = re.search(r'\d+', channel_name)
        return int(match.group()) if match else float('inf')

    # 创建工作线程
    print(f"[{datetime.datetime.now()}] 开始频道测速")
    num_workers = 10
    threads = []
    for _ in range(num_workers):
        t = threading.Thread(target=worker, daemon=True)
        t.start()
        threads.append(t)

    # 填充任务队列
    for result in all_results:
        parts = result.split(',', 1)
        if len(parts) == 2:
            channel_name, channel_url = parts
            task_queue.put((channel_name, channel_url))

    # 等待所有任务完成
    task_queue.join()
    
    # 清理工作线程
    for _ in range(num_workers):
        task_queue.put(("STOP", ""))
    
    for t in threads:
        t.join(timeout=1)

    # 对结果排序
    print(f"[{datetime.datetime.now()}] 排序结果")
    results.sort(key=lambda x: (x[0], -float(x[2].split()[0])))
    results.sort(key=lambda x: channel_key(x[0]))

    # 保存速度结果
    with open("speed_results.txt", 'w', encoding='utf-8') as file:
        for result in results:
            file.write(f"{result[0]},{result[1]},{result[2]}\n")

    # 生成IPTV文件
    print(f"[{datetime.datetime.now()}] 生成IPTV文件")
    result_counter = 8  # 每个频道保留的最佳源数量

    with open("iptv0905.txt", 'w', encoding='utf-8') as file:
        # 央视频道
        file.write('央视频道,#genre#\n')
        cctv_counter = {}
        for result in results:
            channel_name, channel_url, _ = result
            if 'CCTV' in channel_name:
                count = cctv_counter.get(channel_name, 0)
                if count < result_counter:
                    file.write(f"{channel_name},{channel_url}\n")
                    cctv_counter[channel_name] = count + 1
        
        # 卫视频道
        file.write('\n卫视频道,#genre#\n')
        tv_counter = {}
        for result in results:
            channel_name, channel_url, _ = result
            if '卫视' in channel_name:
                count = tv_counter.get(channel_name, 0)
                if count < result_counter:
                    file.write(f"{channel_name},{channel_url}\n")
                    tv_counter[channel_name] = count + 1
        
        # 其他频道
        file.write('\n其他频道,#genre#\n')
        other_counter = {}
        for result in results:
            channel_name, channel_url, _ = result
            if 'CCTV' not in channel_name and '卫视' not in channel_name and '测试' not in channel_name:
                count = other_counter.get(channel_name, 0)
                if count < result_counter:
                    file.write(f"{channel_name},{channel_url}\n")
                    other_counter[channel_name] = count + 1

    print(f"[{datetime.datetime.now()}] 任务完成! 生成文件: iptv0905.txt")

if __name__ == "__main__":
    # 设置更合理的事件循环策略
    policy = asyncio.WindowsSelectorEventLoopPolicy() if os.name == 'nt' else asyncio.DefaultEventLoopPolicy()
    asyncio.set_event_loop_policy(policy)
    
    asyncio.run(main())