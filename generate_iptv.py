import requests
import re
import os
from urllib.parse import urlparse
import time
from concurrent.futures import ThreadPoolExecutor, as_completed

class IPTVGenerator:
    def __init__(self):
        self.assets_dir = "assets"
        self.urls_file = os.path.join(self.assets_dir, "firsturls.txt")
        self.blacklist_file = os.path.join(self.assets_dir, "whitelist-blacklist", "blackhost_count.txt")
        self.sensitive_words_file = os.path.join(self.assets_dir, "sensitive_words.txt")
        self.output_file = os.path.join(self.assets_dir, "live.txt")
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        })
        
        # 存储所有频道，按分类组织
        self.channels = {}
        self.processed_urls = set()
        self.blacklist_hosts = set()
        self.sensitive_words = set()
        
        # 频道分类规则
        self.category_rules = {
            '央视': [r'CCTV', r'央视'],
            '卫视': [r'卫视', r'湖南', r'浙江', r'江苏', r'东方', r'北京', r'广东', r'深圳', r'山东', r'天津', r'湖北', r'四川', r'重庆', r'辽宁', r'吉林', r'黑龙江', r'安徽', r'福建', r'江西', r'河南', r'河北', r'山西', r'陕西', r'甘肃', r'青海', r'海南', r'广西', r'贵州', r'云南', r'内蒙古', r'宁夏', r'新疆', r'西藏'],
            '地方台': [r'地方', r'城市', r'都市', r'县', r'区台', r'民生', r'公共', r'综合'],
            '电影': [r'电影', r'影院', r'MOVIE', r'movie', r'Film', r'film'],
            '体育': [r'体育', r'赛事', r'足球', r'篮球', r'NBA', r'CBA', r'英超', r'西甲', r'德甲', r'意甲', r'欧冠', r'奥运', r'高尔夫', r'网球', r'乒羽', r'搏击', r'赛车'],
            '新闻': [r'新闻', r'NEWS', r'news'],
            '少儿': [r'少儿', r'卡通', r'动漫', r'动画', r'儿童', r'卡通', r'动漫'],
            '纪录片': [r'纪录', r'纪实', r'探索', r'国家地理', r'动物', r'自然', r'历史', r'文化'],
            '综艺': [r'综艺', r'娱乐', r'音乐', r'MTV', r'演唱会', r'戏曲', r'歌舞'],
            '财经': [r'财经', r'经济', r'证券', r'股票', r'财富', r'商业'],
            '教育': [r'教育', r'科教', r'考试', r'学习', r'课堂', r'大学'],
            '国际': [r'国际', r'海外', r'HBO', r'BBC', r'CNN', r'Discovery', r'National Geographic'],
            '其他': []  # 默认分类
        }
    
    def load_blacklist(self):
        """加载黑名单主机"""
        if not os.path.exists(self.blacklist_file):
            print(f"警告: 黑名单文件 {self.blacklist_file} 不存在，跳过黑名单过滤")
            return
            
        try:
            with open(self.blacklist_file, 'r', encoding='utf-8') as f:
                for line in f:
                    line = line.strip()
                    if line and not line.startswith('#'):
                        # 提取主机名
                        if line.startswith(('http://', 'https://')):
                            parsed = urlparse(line)
                            host = parsed.netloc or parsed.path
                        else:
                            host = line
                        self.blacklist_hosts.add(host)
            print(f"加载了 {len(self.blacklist_hosts)} 个黑名单主机")
        except Exception as e:
            print(f"加载黑名单错误: {e}")
    
    def load_sensitive_words(self):
        """加载敏感词列表"""
        if not os.path.exists(self.sensitive_words_file):
            print(f"警告: 敏感词文件 {self.sensitive_words_file} 不存在，跳过敏感词过滤")
            return
            
        try:
            with open(self.sensitive_words_file, 'r', encoding='utf-8') as f:
                content = f.read()
                
                # 移除BOM字符（如果有）
                if content.startswith('\ufeff'):
                    content = content[1:]
                
                lines = content.split('\n')
                for line in lines:
                    line = line.strip()
                    if not line or line.startswith('#'):
                        continue
                    
                    # 处理逗号分隔的多个词
                    if ',' in line:
                        words = line.split(',')
                        for word in words:
                            word = word.strip()
                            # 移除单引号
                            word = word.strip("'\"")
                            if word:
                                self.sensitive_words.add(word.lower())
                    else:
                        # 单一词
                        word = line.strip("'\"")
                        if word:
                            self.sensitive_words.add(word.lower())
            
            print(f"加载了 {len(self.sensitive_words)} 个敏感词")
            print(f"敏感词列表: {list(self.sensitive_words)[:10]}...")  # 显示前10个作为示例
        except Exception as e:
            print(f"加载敏感词错误: {e}")
    
    def is_blacklisted(self, url):
        """检查URL是否在黑名单中"""
        if not self.blacklist_hosts:
            return False
            
        try:
            parsed = urlparse(url)
            host = parsed.netloc
            return host in self.blacklist_hosts
        except:
            return False
    
    def contains_sensitive_words(self, text):
        """检查文本是否包含敏感词"""
        if not self.sensitive_words or not text:
            return False
            
        text_lower = text.lower()
        for word in self.sensitive_words:
            if word in text_lower:
                print(f"过滤敏感词: '{word}' 在内容中: {text[:50]}...")
                return True
        return False
    
    def should_filter_url(self, url):
        """检查URL是否应该被过滤"""
        # 检查黑名单
        if self.is_blacklisted(url):
            print(f"过滤黑名单URL: {url}")
            return True
            
        # 检查文件扩展名
        if any(url.lower().endswith(ext) for ext in ['.mkv', '.mp4']):
            print(f"过滤视频文件URL: {url}")
            return True
            
        # 检查敏感词
        if self.contains_sensitive_words(url):
            print(f"过滤包含敏感词的URL: {url}")
            return True
            
        return False
    
    def should_filter_channel_name(self, name):
        """检查频道名称是否应该被过滤"""
        if not name or name == "未知频道":
            return False
            
        # 检查敏感词
        if self.contains_sensitive_words(name):
            print(f"过滤包含敏感词的频道: {name}")
            return True
            
        return False
    
    def categorize_channel(self, name):
        """根据频道名称自动分类"""
        if not name or name == "未知频道":
            return "其他"
        
        # 检查是否应该过滤
        if self.should_filter_channel_name(name):
            return None
        
        # 按分类规则匹配
        for category, patterns in self.category_rules.items():
            for pattern in patterns:
                if re.search(pattern, name, re.IGNORECASE):
                    return category
        
        # 默认分类
        return "其他"
    
    def extract_urls_from_file(self):
        """从firsturls.txt文件中提取所有URL"""
        urls_with_category = []
        
        try:
            with open(self.urls_file, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # 移除git冲突标记
            content = re.sub(r'<<<<<<< HEAD\n.*?\n=======\n.*?\n>>>>>>> [a-f0-9]+\n', '', content, flags=re.DOTALL)
            
            lines = content.split('\n')
            current_category = "未分类"
            
            for line in lines:
                line = line.strip()
                if not line or line.startswith('#'):
                    # 检查是否是分类注释
                    if '#' in line and ('频道' in line or 'TV' in line or '直播' in line):
                        match = re.search(r'#(.+)$', line)
                        if match:
                            current_category = match.group(1).strip()
                    continue
                
                # 提取URL和可能的分类
                url = line
                category = current_category
                
                # 如果URL中包含#分类，使用URL中的分类
                if '#' in line:
                    parts = line.split('#', 1)
                    url = parts[0].strip()
                    if len(parts) > 1 and parts[1].strip():
                        category = parts[1].strip()
                
                # 检查URL是否包含敏感词
                if self.contains_sensitive_words(url) or self.contains_sensitive_words(category):
                    print(f"跳过包含敏感词的URL或分类: {url} - {category}")
                    continue
                
                if url and url.startswith(('http://', 'https://')):
                    urls_with_category.append((url, category))
                    
        except Exception as e:
            print(f"读取URL文件错误: {e}")
            
        return urls_with_category
    
    def parse_m3u_content(self, content, source_category):
        """解析M3U格式内容"""
        channels = []
        lines = content.split('\n')
        i = 0
        
        # 检查整个内容是否包含敏感词
        if self.contains_sensitive_words(content):
            print(f"跳过包含敏感词的M3U内容，分类: {source_category}")
            return channels
        
        while i < len(lines):
            line = lines[i].strip()
            if line.startswith('#EXTINF:'):
                # 提取频道信息
                extinf_line = line
                if i + 1 < len(lines):
                    url_line = lines[i + 1].strip()
                    if url_line and not url_line.startswith('#'):
                        # 解析频道名称
                        channel_name = "未知频道"
                        match = re.search(r',([^,]+)$', extinf_line)
                        if match:
                            channel_name = match.group(1).strip()
                        
                        # 使用原始名称，不进行标准化
                        original_name = channel_name
                        
                        # 自动分类
                        category = self.categorize_channel(original_name)
                        if category is None:  # 被敏感词过滤
                            i += 2
                            continue
                        
                        # 过滤URL和频道名称
                        if not self.should_filter_url(url_line) and not self.should_filter_channel_name(original_name):
                            channels.append({
                                'name': original_name,
                                'url': url_line,
                                'category': category,
                                'source': 'm3u',
                                'source_category': source_category
                            })
                        i += 1
            i += 1
            
        return channels
    
    def parse_txt_content(self, content, source_category):
        """解析文本格式内容"""
        channels = []
        lines = content.split('\n')
        
        # 检查整个内容是否包含敏感词
        if self.contains_sensitive_words(content):
            print(f"跳过包含敏感词的TXT内容，分类: {source_category}")
            return channels
        
        for line in lines:
            line = line.strip()
            if not line or line.startswith('#'):
                continue
                
            # 多种分隔符尝试：逗号、空格、制表符等
            if ',' in line:
                parts = line.split(',', 1)
                if len(parts) == 2:
                    name, url = parts[0].strip(), parts[1].strip()
                    if url.startswith(('http://', 'https://', 'rtmp://', 'rtsp://')):
                        # 使用原始名称，不进行标准化
                        original_name = name
                        
                        # 自动分类
                        category = self.categorize_channel(original_name)
                        if category is None:  # 被敏感词过滤
                            continue
                        
                        # 过滤URL和频道名称
                        if not self.should_filter_url(url) and not self.should_filter_channel_name(original_name):
                            channels.append({
                                'name': original_name,
                                'url': url,
                                'category': category,
                                'source': 'txt',
                                'source_category': source_category
                            })
            elif 'http' in line:
                # 尝试提取URL和名称
                match = re.search(r'^(.*?)(http[s]?://\S+)$', line)
                if match:
                    name, url = match.group(1).strip(), match.group(2).strip()
                    if not name:
                        name = "未知频道"
                    
                    # 使用原始名称，不进行标准化
                    original_name = name
                    
                    # 自动分类
                    category = self.categorize_channel(original_name)
                    if category is None:  # 被敏感词过滤
                        continue
                    
                    # 过滤URL和频道名称
                    if not self.should_filter_url(url) and not self.should_filter_channel_name(original_name):
                        channels.append({
                            'name': original_name,
                            'url': url,
                            'category': category,
                            'source': 'txt',
                            'source_category': source_category
                        })
                else:
                    # 如果整行就是URL
                    if line.startswith(('http://', 'https://')):
                        # 过滤URL
                        if not self.should_filter_url(line):
                            # 自动分类为"其他"
                            category = self.categorize_channel("未知频道")
                            if category is not None:  # 未被敏感词过滤
                                channels.append({
                                    'name': '未知频道',
                                    'url': line,
                                    'category': category,
                                    'source': 'txt',
                                    'source_category': source_category
                                })
        
        return channels
    
    def fetch_url_content(self, url, source_category):
        """获取URL内容并解析"""
        if url in self.processed_urls:
            return []
            
        try:
            print(f"正在获取: {url}")
            response = self.session.get(url, timeout=10)
            response.encoding = 'utf-8'
            
            if response.status_code == 200:
                content = response.text
                self.processed_urls.add(url)
                
                # 根据内容类型解析
                if content.strip().startswith('#EXTM3U'):
                    return self.parse_m3u_content(content, source_category)
                else:
                    return self.parse_txt_content(content, source_category)
            else:
                print(f"请求失败 {url}: 状态码 {response.status_code}")
                
        except Exception as e:
            print(f"获取URL内容错误 {url}: {e}")
            
        return []
    
    def is_duplicate_channel(self, channel):
        """检查频道是否重复"""
        for existing_channels in self.channels.values():
            for existing_channel in existing_channels:
                if existing_channel['url'] == channel['url']:
                    return True
        return False
    
    def add_channel(self, channel):
        """添加频道到对应分类"""
        category = channel['category']
        if category not in self.channels:
            self.channels[category] = []
        
        # 检查重复
        if not self.is_duplicate_channel(channel):
            self.channels[category].append(channel)
            return True
        return False
    
    def generate_live_txt(self):
        """生成最终的live.txt文件"""
        try:
            with open(self.output_file, 'w', encoding='utf-8') as f:
                f.write("# IPTV直播源 - 自动生成\n")
                f.write(f"# 生成时间: {time.strftime('%Y-%m-%d %H:%M:%S')}\n")
                
                total_channels = sum(len(channels) for channels in self.channels.values())
                f.write(f"# 总频道数: {total_channels}\n")
                f.write(f"# 分类数: {len(self.channels)}\n")
                f.write(f"# 已过滤黑名单主机: {len(self.blacklist_hosts)}\n")
                f.write(f"# 已过滤敏感词: {len(self.sensitive_words)}\n")
                f.write(f"# 已过滤.mkv/.mp4文件\n\n")
                
                # 按分类排序输出
                sorted_categories = sorted(self.channels.keys())
                for category in sorted_categories:
                    channels = self.channels[category]
                    f.write(f"# {category} - 共{len(channels)}个频道\n")
                    for channel in channels:
                        f.write(f"{channel['name']},{channel['url']}\n")
                    f.write("\n")
                    
            print(f"成功生成 live.txt，包含 {len(self.channels)} 个分类，{total_channels} 个频道")
            
        except Exception as e:
            print(f"生成文件错误: {e}")
    
    def run(self):
        """主运行函数"""
        print("开始获取IPTV频道...")
        
        # 检查文件是否存在
        if not os.path.exists(self.urls_file):
            print(f"错误: {self.urls_file} 文件不存在!")
            return
        
        # 加载黑名单和敏感词
        self.load_blacklist()
        self.load_sensitive_words()
        
        # 提取URL
        urls_with_category = self.extract_urls_from_file()
        print(f"找到 {len(urls_with_category)} 个URL")
        
        if not urls_with_category:
            print("没有找到有效的URL，请检查firsturls.txt文件格式")
            return
        
        # 使用多线程获取内容
        with ThreadPoolExecutor(max_workers=5) as executor:
            future_to_url = {
                executor.submit(self.fetch_url_content, url, category): (url, category) 
                for url, category in urls_with_category
            }
            
            for future in as_completed(future_to_url):
                url, category = future_to_url[future]
                try:
                    channels = future.result()
                    added_count = 0
                    for channel in channels:
                        if self.add_channel(channel):
                            added_count += 1
                    if added_count > 0:
                        print(f"从 {url} 添加了 {added_count} 个频道到分类 '{channel['category']}' (原分类: {category})")
                except Exception as e:
                    print(f"处理URL错误 {url}: {e}")
        
        # 生成最终文件
        total_channels = sum(len(channels) for channels in self.channels.values())
        print(f"\n总共获取到 {total_channels} 个唯一频道")
        
        # 显示分类统计
        print("\n分类统计:")
        for category, channels in sorted(self.channels.items()):
            print(f"  {category}: {len(channels)} 个频道")
        
        self.generate_live_txt()
        print("完成!")

def main():
    # 检查assets文件夹是否存在
    if not os.path.exists("assets"):
        print("创建assets文件夹...")
        os.makedirs("assets")
        print("请将firsturls.txt文件放入assets文件夹中")
        return
    
    # 运行生成器
    generator = IPTVGenerator()
    generator.run()

if __name__ == "__main__":
    main()