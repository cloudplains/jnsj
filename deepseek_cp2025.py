import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from matplotlib import font_manager
import requests
import base64
from io import BytesIO
import os
import webbrowser
import sys
from datetime import datetime, timedelta
import random
import warnings

# 过滤matplotlib字体警告
warnings.filterwarnings("ignore", category=UserWarning)

class LotteryAnalyzer:
    def __init__(self, file_path):
        self.file_path = file_path
        self.dlt_df = None
        self.ssq_df = None
        self.pl5_df = None  # 新增排列五数据
        
        # 设置中文字体
        self._setup_chinese_font()
        
        # 大乐透配置
        self.dlt_front_cols = ['前区1', '前区2', '前区3', '前区4', '前区5']
        self.dlt_back_cols = ['后区1', '后区2']
        self.dlt_front_range = (1, 35)
        self.dlt_back_range = (1, 12)
        
        # 双色球配置
        self.ssq_red_cols = ['红球1', '红球2', '红球3', '红球4', '红球5', '红球6']
        self.ssq_blue_cols = ['蓝球']
        self.ssq_red_range = (1, 33)
        self.ssq_blue_range = (1, 16)
        
        # 排列五配置
        self.pl5_cols = ['万位', '千位', '百位', '十位', '个位']  # 假设列名
        self.pl5_range = (0, 9)  # 每个位置都是0-9
        
    def _setup_chinese_font(self):
        """设置中文字体"""
        try:
            # 尝试使用系统中已有的中文字体
            system_fonts = ['SimHei', 'Microsoft YaHei', 'DejaVu Sans', 'Arial Unicode MS', 'SimSun']
            
            for font_name in system_fonts:
                if font_name in [f.name for f in font_manager.fontManager.ttflist]:
                    plt.rcParams['font.family'] = font_name
                    plt.rcParams['axes.unicode_minus'] = False  # 解决负号显示问题
                    break
            else:
                # 如果没有找到中文字体，使用默认字体并禁用中文显示
                plt.rcParams['font.family'] = 'sans-serif'
        except:
            # 如果所有尝试都失败，使用默认设置
            pass
    
    def validate_data(self):
        """验证数据文件"""
        print("=== 数据验证 ===")
        try:
            # 检查文件是否存在
            if not os.path.exists(self.file_path):
                print(f"✗ 文件不存在：{self.file_path}")
                return {'dlt': False, 'ssq': False, 'pl5': False}
            
            # 读取Excel文件
            excel_file = pd.ExcelFile(self.file_path)
            available_sheets = excel_file.sheet_names
            print(f"可用工作表：{available_sheets}")
            
            results = {}
            
            # 验证大乐透数据
            if "dltall" in available_sheets:
                self.dlt_df = excel_file.parse("dltall")
                print("✓ 大乐透数据验证通过")
                print(f"  数据行数：{len(self.dlt_df)}")
                
                # 转换为整数类型
                try:
                    self.dlt_df[self.dlt_front_cols] = self.dlt_df[self.dlt_front_cols].astype(int)
                    self.dlt_df[self.dlt_back_cols] = self.dlt_df[self.dlt_back_cols].astype(int)
                    results['dlt'] = True
                except Exception as e:
                    print(f"✗ 大乐透数据转换失败：{str(e)}")
                    results['dlt'] = False
            else:
                print("✗ 大乐透工作表不存在")
                results['dlt'] = False
            
            # 验证双色球数据
            if "ssq" in available_sheets:
                self.ssq_df = excel_file.parse("ssq")
                print("✓ 双色球数据验证通过")
                print(f"  数据行数：{len(self.ssq_df)}")
                
                # 转换为整数类型
                try:
                    self.ssq_df[self.ssq_red_cols] = self.ssq_df[self.ssq_red_cols].astype(int)
                    self.ssq_df[self.ssq_blue_cols] = self.ssq_df[self.ssq_blue_cols].astype(int)
                    results['ssq'] = True
                except Exception as e:
                    print(f"✗ 双色球数据转换失败：{str(e)}")
                    results['ssq'] = False
            else:
                print("✗ 双色球工作表不存在")
                results['ssq'] = False
            
            # 验证排列五数据
            if "pl5" in available_sheets:
                self.pl5_df = excel_file.parse("pl5")
                print("✓ 排列五数据验证通过")
                print(f"  数据行数：{len(self.pl5_df)}")
                print(f"  列名：{self.pl5_df.columns.tolist()}")
                
                # 检查列名并尝试转换
                try:
                    # 先检查是否有各个位置的列
                    has_position_columns = False
                    for col in self.pl5_cols:
                        if col in self.pl5_df.columns:
                            has_position_columns = True
                            self.pl5_df[col] = pd.to_numeric(self.pl5_df[col], errors='coerce').fillna(0).astype(int)
                    
                    # 如果没有单独的列，尝试从"开奖号码"列解析
                    if not has_position_columns and '开奖号码' in self.pl5_df.columns:
                        print("   从'开奖号码'列解析数据...")
                        # 清理开奖号码列：移除空格，只保留数字
                        self.pl5_df['开奖号码_clean'] = self.pl5_df['开奖号码'].astype(str).str.replace(r'\s+', '', regex=True)
                        # 确保是5位数字
                        self.pl5_df['开奖号码_clean'] = self.pl5_df['开奖号码_clean'].str.zfill(5)
                        # 提取每个位置的数字
                        for i, col in enumerate(self.pl5_cols):
                            self.pl5_df[col] = self.pl5_df['开奖号码_clean'].str[i].astype(int)
                        
                        print(f"   前5行数据：{self.pl5_df[self.pl5_cols].head().values.tolist()}")
                    
                    results['pl5'] = True
                except Exception as e:
                    print(f"✗ 排列五数据转换失败：{str(e)}")
                    print(f"  数据示例：{self.pl5_df.head(3).to_dict() if len(self.pl5_df) > 0 else '空数据'}")
                    results['pl5'] = False
            else:
                print("✗ 排列五工作表不存在")
                results['pl5'] = False
            
            return results
            
        except Exception as e:
            print(f"✗ 读取文件失败：{str(e)}")
            return {'dlt': False, 'ssq': False, 'pl5': False}
    
    def get_latest_draw_info(self):
        """获取最新开奖信息"""
        latest_info = {}
        
        # 获取大乐透最新开奖信息
        if self.dlt_df is not None and len(self.dlt_df) > 0:
            latest_dlt = self.dlt_df.iloc[-1]
            # 假设数据中有期号列，如果没有则用索引
            dlt_period = latest_dlt.get('期号', f"第{len(self.dlt_df)}期")
            dlt_date = latest_dlt.get('开奖日期', '未知日期')
            dlt_front = [latest_dlt[col] for col in self.dlt_front_cols]
            dlt_back = [latest_dlt[col] for col in self.dlt_back_cols]
            
            latest_info['dlt'] = {
                'period': dlt_period,
                'date': dlt_date,
                'front_numbers': dlt_front,
                'back_numbers': dlt_back
            }
        
        # 获取双色球最新开奖信息
        if self.ssq_df is not None and len(self.ssq_df) > 0:
            latest_ssq = self.ssq_df.iloc[-1]
            # 假设数据中有期号列，如果没有则用索引
            ssq_period = latest_ssq.get('期号', f"第{len(self.ssq_df)}期")
            ssq_date = latest_ssq.get('开奖日期', '未知日期')
            ssq_red = [latest_ssq[col] for col in self.ssq_red_cols]
            ssq_blue = [latest_ssq[col] for col in self.ssq_blue_cols]
            
            latest_info['ssq'] = {
                'period': ssq_period,
                'date': ssq_date,
                'red_numbers': ssq_red,
                'blue_number': ssq_blue[0] if ssq_blue else '未知'
            }
        
        # 获取排列五最新开奖信息
        if self.pl5_df is not None and len(self.pl5_df) > 0:
            latest_pl5 = self.pl5_df.iloc[-1]
            # 假设数据中有期号列
            pl5_period = latest_pl5.get('期号', f"第{len(self.pl5_df)}期")
            pl5_date = latest_pl5.get('开奖日期', '未知日期')
            
            # 获取各个位置的数字
            pl5_numbers = []
            for col in self.pl5_cols:
                if col in latest_pl5 and not pd.isna(latest_pl5[col]):
                    try:
                        pl5_numbers.append(int(latest_pl5[col]))
                    except (ValueError, TypeError):
                        # 如果转换失败，尝试从开奖号码字符串中提取
                        if '开奖号码' in latest_pl5 and not pd.isna(latest_pl5['开奖号码']):
                            num_str = str(latest_pl5['开奖号码']).replace(' ', '').strip()
                            if len(num_str) >= 5 and num_str.isdigit():
                                pl5_numbers = [int(d) for d in num_str[:5]]
                                break
            
            # 如果pl5_numbers为空或长度不足，使用默认值
            if len(pl5_numbers) < 5:
                pl5_numbers = [0] * 5
            
            latest_info['pl5'] = {
                'period': pl5_period,
                'date': pl5_date,
                'numbers': pl5_numbers[:5]  # 只取前5位
            }
        
        return latest_info
    
    def analyze_dlt(self):
        """分析大乐透数据"""
        if self.dlt_df is None:
            return None
            
        print("\n=== 大乐透数据分析 ===")
        
        # 获取最近30期数据进行分析
        recent_30_data = self.dlt_df.tail(30)
        
        # 获取所有数据进行分析
        front_numbers = pd.concat([self.dlt_df[col] for col in self.dlt_front_cols])
        back_numbers = pd.concat([self.dlt_df[col] for col in self.dlt_back_cols])
        
        # 最近30期数据分析
        recent_front_numbers = pd.concat([recent_30_data[col] for col in self.dlt_front_cols])
        recent_back_numbers = pd.concat([recent_30_data[col] for col in self.dlt_back_cols])
        
        # 频率统计（全部数据）
        front_freq = front_numbers.value_counts().sort_index()
        back_freq = back_numbers.value_counts().sort_index()
        
        # 频率统计（最近30期）
        recent_front_freq = recent_front_numbers.value_counts()
        recent_back_freq = recent_back_numbers.value_counts()
        
        # 获取热门号码（最近30期出现次数最多的1-2个）
        recent_front_hot = recent_front_freq.head(2).index.tolist()
        recent_back_hot = recent_back_freq.head(1).index.tolist()  # 后区只取1个热门
        
        # 获取冷门号码（最近30期出现次数最少或未出现的）
        # 前区冷门：最近30期出现0次或1次的号码
        recent_front_cold = []
        for num in range(self.dlt_front_range[0], self.dlt_front_range[1] + 1):
            if num not in recent_front_freq.index or recent_front_freq[num] <= 1:
                recent_front_cold.append(num)
        # 如果冷门号码太多，取出现次数最少的5个
        if len(recent_front_cold) > 10:
            recent_front_cold = recent_front_freq.tail(5).index.tolist()
        
        # 后区冷门：最近30期出现次数最少的1-2个号码
        if len(recent_back_freq) > 0:
            # 找出出现次数最少的2个号码
            recent_back_cold = recent_back_freq.tail(2).index.tolist()
        else:
            # 如果没有频率数据，随机选择2个不热门的
            all_back_numbers = list(range(self.dlt_back_range[0], self.dlt_back_range[1] + 1))
            if recent_back_hot:
                # 排除热门号码
                available = [num for num in all_back_numbers if num not in recent_back_hot]
                recent_back_cold = random.sample(available, min(2, len(available)))
            else:
                recent_back_cold = random.sample(all_back_numbers, min(2, len(all_back_numbers)))
        
        # 奇偶统计
        front_odd = (front_numbers % 2 == 1).sum()
        front_even = (front_numbers % 2 == 0).sum()
        back_odd = (back_numbers % 2 == 1).sum()
        back_even = (back_numbers % 2 == 0).sum()
        
        # 区间统计
        def dlt_front_interval(num):
            if num <= 12: return '1-12'
            elif num <= 24: return '13-24'
            else: return '25-35'
        
        def dlt_back_interval(num):
            return '1-6' if num <= 6 else '7-12'
        
        front_intervals = front_numbers.apply(dlt_front_interval)
        back_intervals = back_numbers.apply(dlt_back_interval)
        
        print(f"   前区热门号码(最近30期)：{recent_front_hot}")
        print(f"   前区冷门号码(最近30期)：{recent_front_cold[:5]}...")  # 只显示前5个
        print(f"   后区热门号码(最近30期)：{recent_back_hot}")
        print(f"   后区冷门号码(最近30期)：{recent_back_cold}")
        print(f"   前区奇偶比：{front_odd}/{front_even} ({front_odd/len(front_numbers):.1%}:{front_even/len(front_numbers):.1%})")
        
        return {
            'front_numbers': front_numbers,
            'back_numbers': back_numbers,
            'front_freq': front_freq,
            'back_freq': back_freq,
            'recent_front_freq': recent_front_freq,
            'recent_back_freq': recent_back_freq,
            'recent_front_hot': recent_front_hot,
            'recent_front_cold': recent_front_cold[:5],  # 只返回前5个冷门
            'recent_back_hot': recent_back_hot,
            'recent_back_cold': recent_back_cold[:3],    # 只返回前3个冷门
            'front_odd': front_odd,
            'front_even': front_even,
            'back_odd': back_odd,
            'back_even': back_even,
            'front_intervals': front_intervals.value_counts(),
            'back_intervals': back_intervals.value_counts()
        }
    
    def analyze_ssq(self):
        """分析双色球数据"""
        if self.ssq_df is None:
            return None
            
        print("\n=== 双色球数据分析 ===")
        
        # 获取最近30期数据进行分析
        recent_30_data = self.ssq_df.tail(30)
        
        # 获取所有数据进行分析
        red_numbers = pd.concat([self.ssq_df[col] for col in self.ssq_red_cols])
        blue_numbers = pd.concat([self.ssq_df[col] for col in self.ssq_blue_cols])
        
        # 最近30期数据分析
        recent_red_numbers = pd.concat([recent_30_data[col] for col in self.ssq_red_cols])
        recent_blue_numbers = pd.concat([recent_30_data[col] for col in self.ssq_blue_cols])
        
        # 频率统计（全部数据）
        red_freq = red_numbers.value_counts().sort_index()
        blue_freq = blue_numbers.value_counts().sort_index()
        
        # 频率统计（最近30期）
        recent_red_freq = recent_red_numbers.value_counts()
        recent_blue_freq = recent_blue_numbers.value_counts()
        
        # 获取热门号码（最近30期出现次数最多的）
        recent_red_hot = recent_red_freq.head(2).index.tolist()
        recent_blue_hot = recent_blue_freq.head(1).index.tolist()
        
        # 获取冷门号码（最近30期出现次数最少或未出现的）
        # 红球冷门：最近30期出现0次或1次的号码
        recent_red_cold = []
        for num in range(self.ssq_red_range[0], self.ssq_red_range[1] + 1):
            if num not in recent_red_freq.index or recent_red_freq[num] <= 1:
                recent_red_cold.append(num)
        # 如果冷门号码太多，取出现次数最少的5个
        if len(recent_red_cold) > 10:
            recent_red_cold = recent_red_freq.tail(5).index.tolist()
        
        # 蓝球冷门：最近30期出现次数最少的1-2个号码
        if len(recent_blue_freq) > 0:
            # 找出出现次数最少的2个号码
            recent_blue_cold = recent_blue_freq.tail(2).index.tolist()
        else:
            # 如果没有频率数据，随机选择2个不热门的
            all_blue_numbers = list(range(self.ssq_blue_range[0], self.ssq_blue_range[1] + 1))
            if recent_blue_hot:
                # 排除热门号码
                available = [num for num in all_blue_numbers if num not in recent_blue_hot]
                recent_blue_cold = random.sample(available, min(2, len(available)))
            else:
                recent_blue_cold = random.sample(all_blue_numbers, min(2, len(all_blue_numbers)))
        
        # 奇偶统计
        red_odd = (red_numbers % 2 == 1).sum()
        red_even = (red_numbers % 2 == 0).sum()
        blue_odd = (blue_numbers % 2 == 1).sum()
        blue_even = (blue_numbers % 2 == 0).sum()
        
        # 区间统计
        def ssq_red_interval(num):
            if num <= 11: return '1-11'
            elif num <= 22: return '12-22'
            else: return '23-33'
        
        def ssq_blue_interval(num):
            return '1-8' if num <= 8 else '9-16'
        
        red_intervals = red_numbers.apply(ssq_red_interval)
        blue_intervals = blue_numbers.apply(ssq_blue_interval)
        
        print(f"   红球热门号码(最近30期)：{recent_red_hot}")
        print(f"   红球冷门号码(最近30期)：{recent_red_cold[:5]}...")  # 只显示前5个
        print(f"   蓝球热门号码(最近30期)：{recent_blue_hot}")
        print(f"   蓝球冷门号码(最近30期)：{recent_blue_cold}")
        print(f"   红球奇偶比：{red_odd}/{red_even} ({red_odd/len(red_numbers):.1%}:{red_even/len(red_numbers):.1%})")
        
        return {
            'red_numbers': red_numbers,
            'blue_numbers': blue_numbers,
            'red_freq': red_freq,
            'blue_freq': blue_freq,
            'recent_red_freq': recent_red_freq,
            'recent_blue_freq': recent_blue_freq,
            'recent_red_hot': recent_red_hot,
            'recent_red_cold': recent_red_cold[:5],  # 只返回前5个冷门
            'recent_blue_hot': recent_blue_hot,
            'recent_blue_cold': recent_blue_cold[:3],  # 只返回前3个冷门
            'red_odd': red_odd,
            'red_even': red_even,
            'blue_odd': blue_odd,
            'blue_even': blue_even,
            'red_intervals': red_intervals.value_counts(),
            'blue_intervals': blue_intervals.value_counts()
        }
    
    def analyze_pl5(self):
        """分析排列五数据"""
        if self.pl5_df is None:
            return None
            
        print("\n=== 排列五数据分析 ===")
        
        # 检查是否有数据
        if len(self.pl5_df) == 0:
            print("   警告：排列五数据为空")
            return None
        
        # 获取最近30期数据进行分析
        recent_30_data = self.pl5_df.tail(30)
        
        # 存储每位数字的频率
        position_freq = {}
        position_numbers = {}
        recent_position_freq = {}
        
        # 存储每个位置的热门和冷门号码
        position_hot = {}
        position_cold = {}
        
        for i, col in enumerate(self.pl5_cols):
            if col in self.pl5_df.columns:
                # 确保数据类型正确
                numbers = pd.to_numeric(self.pl5_df[col], errors='coerce').fillna(0).astype(int)
                position_numbers[col] = numbers
                freq = numbers.value_counts().sort_index()
                position_freq[col] = freq
                
                # 最近30期数据
                recent_numbers = pd.to_numeric(recent_30_data[col], errors='coerce').fillna(0).astype(int)
                recent_freq = recent_numbers.value_counts()
                recent_position_freq[col] = recent_freq
                
                # 获取热门和冷门号码（基于最近30期）
                # 热门号码：出现次数最多的前2个
                recent_hot = recent_freq.head(2).index.tolist() if len(recent_freq) > 0 else []
                position_hot[col] = recent_hot
                
                # 冷门号码：最近30期出现次数最少或未出现的
                recent_cold = []
                for num in range(0, 10):
                    if num not in recent_freq.index or recent_freq[num] <= 1:
                        recent_cold.append(num)
                # 如果冷门号码太多，取出现次数最少的3个
                if len(recent_cold) > 5:
                    recent_cold = recent_freq.tail(3).index.tolist() if len(recent_freq) >= 3 else recent_cold[:3]
                position_cold[col] = recent_cold
                
                print(f"   {col}热门数字(最近30期)：{recent_hot}")
                print(f"   {col}冷门数字(最近30期)：{recent_cold}")
        
        # 如果没有数据，返回空结果
        if not position_numbers:
            print("   警告：未找到有效的排列五位置数据")
            return None
        
        # 奇偶统计
        odd_even_stats = {}
        for col, numbers in position_numbers.items():
            odd = (numbers % 2 == 1).sum()
            even = (numbers % 2 == 0).sum()
            odd_even_stats[col] = {'odd': odd, 'even': even}
        
        # 大小统计 (0-4为小，5-9为大)
        size_stats = {}
        for col, numbers in position_numbers.items():
            small = ((numbers >= 0) & (numbers <= 4)).sum()
            big = ((numbers >= 5) & (numbers <= 9)).sum()
            size_stats[col] = {'small': small, 'big': big}
        
        # 质合统计
        prime_stats = {}
        primes = {2, 3, 5, 7}  # 0-9中的质数
        for col, numbers in position_numbers.items():
            prime = numbers.isin(primes).sum()
            composite = len(numbers) - prime
            prime_stats[col] = {'prime': prime, 'composite': composite}
        
        return {
            'position_numbers': position_numbers,
            'position_freq': position_freq,
            'recent_position_freq': recent_position_freq,
            'position_hot': position_hot,
            'position_cold': position_cold,
            'odd_even_stats': odd_even_stats,
            'size_stats': size_stats,
            'prime_stats': prime_stats
        }
    
    def recommend_dlt_numbers(self):
        """推荐大乐透号码 - 改进版"""
        if self.dlt_df is None:
            return None
            
        print("\n=== 大乐透号码推荐 ===")
        
        # 获取最近30期数据
        recent_data = self.dlt_df.tail(30)
        recent_front = pd.concat([recent_data[col] for col in self.dlt_front_cols])
        recent_back = pd.concat([recent_data[col] for col in self.dlt_back_cols])
        
        # 计算近期频率
        recent_front_freq = recent_front.value_counts()
        recent_back_freq = recent_back.value_counts()
        
        # 获取所有可能号码
        all_front = list(range(self.dlt_front_range[0], self.dlt_front_range[1] + 1))
        all_back = list(range(self.dlt_back_range[0], self.dlt_back_range[1] + 1))
        
        # 前区号码选择策略：2个热门 + 2个冷门 + 1个随机
        # 热门号码（最近30期出现次数最多的）
        front_hot = recent_front_freq.head(10).index.tolist()
        # 冷门号码（最近30期出现次数最少的，或未出现的）
        front_cold = [num for num in all_front if num not in recent_front_freq.index]
        if len(front_cold) < 2:  # 如果冷门号码不足，选择出现次数最少的
            front_cold = recent_front_freq.tail(10).index.tolist()
        
        # 随机选择热门和冷门号码
        selected_hot = random.sample(front_hot, 2) if len(front_hot) >= 2 else front_hot
        selected_cold = random.sample(front_cold, 2) if len(front_cold) >= 2 else front_cold
        
        # 随机号码（排除已选的）
        remaining = [num for num in all_front if num not in selected_hot + selected_cold]
        random_num = random.choice(remaining) if remaining else random.choice(all_front)
        
        front_numbers = selected_hot + selected_cold + [random_num]
        front_numbers = sorted(front_numbers)
        
        # 后区号码选择策略：1个热门 + 1个随机
        # 热门号码
        back_hot = recent_back_freq.head(6).index.tolist()
        selected_back_hot = random.choice(back_hot) if back_hot else random.choice(all_back)
        
        # 随机号码（排除已选的）
        back_remaining = [num for num in all_back if num != selected_back_hot]
        random_back = random.choice(back_remaining) if back_remaining else random.choice(all_back)
        
        back_numbers = [selected_back_hot, random_back]
        back_numbers = sorted(back_numbers)
        
        print(f"🎯 推荐号码：")
        print(f"   前区：{' '.join(map(str, front_numbers))}")
        print(f"   后区：{' '.join(map(str, back_numbers))}")
        print(f"   策略：前区(2热:{selected_hot} + 2冷:{selected_cold} + 1随机:{random_num}) | 后区(1热:{selected_back_hot} + 1随机:{random_back})")
        print(f"   分析期数：最近30期")
        
        return front_numbers, back_numbers
    
    def recommend_ssq_numbers(self):
        """推荐双色球号码 - 改进版"""
        if self.ssq_df is None:
            return None
            
        print("\n=== 双色球号码推荐 ===")
        
        # 获取最近30期数据
        recent_data = self.ssq_df.tail(30)
        recent_red = pd.concat([recent_data[col] for col in self.ssq_red_cols])
        recent_blue = pd.concat([recent_data[col] for col in self.ssq_blue_cols])
        
        # 计算近期频率
        recent_red_freq = recent_red.value_counts()
        recent_blue_freq = recent_blue.value_counts()
        
        # 获取所有可能号码
        all_red = list(range(self.ssq_red_range[0], self.ssq_red_range[1] + 1))
        all_blue = list(range(self.ssq_blue_range[0], self.ssq_blue_range[1] + 1))
        
        # 红球号码选择策略：2个热门 + 2个温门 + 2个冷门
        total_red = len(recent_red_freq)
        
        # 热门号码（前1/3）
        hot_count = max(2, total_red // 3)
        red_hot = recent_red_freq.head(hot_count).index.tolist()
        
        # 冷门号码（后1/3）
        red_cold = recent_red_freq.tail(hot_count).index.tolist()
        # 如果冷门号码不足，添加未出现的号码
        missing_cold = [num for num in all_red if num not in recent_red_freq.index]
        red_cold.extend(missing_cold[:max(0, 4 - len(red_cold))])
        
        # 温门号码（中间1/3）
        warm_start = hot_count
        warm_end = total_red - hot_count
        red_warm = recent_red_freq.iloc[warm_start:warm_end].index.tolist() if warm_start < warm_end else []
        
        # 随机选择各类号码
        selected_hot = random.sample(red_hot, 2) if len(red_hot) >= 2 else red_hot
        selected_warm = random.sample(red_warm, 2) if len(red_warm) >= 2 else []
        selected_cold = random.sample(red_cold, 2) if len(red_cold) >= 2 else red_cold
        
        # 如果某类号码不足，从其他类别补充
        red_numbers = selected_hot + selected_warm + selected_cold
        while len(red_numbers) < 6:
            if len(selected_hot) < 2:
                additional = [num for num in red_hot if num not in red_numbers]
                if additional:
                    selected_hot.append(random.choice(additional))
            elif len(selected_warm) < 2:
                additional = [num for num in red_warm if num not in red_numbers]
                if additional:
                    selected_warm.append(random.choice(additional))
            else:
                additional = [num for num in red_cold if num not in red_numbers]
                if additional:
                    selected_cold.append(random.choice(additional))
            red_numbers = selected_hot + selected_warm + selected_cold
        
        red_numbers = sorted(red_numbers[:6])  # 确保只有6个号码
        
        # 蓝球号码选择策略：热门号码
        blue_hot = recent_blue_freq.head(5).index.tolist()
        blue_number = random.choice(blue_hot) if blue_hot else random.choice(all_blue)
        
        print(f"🎯 推荐号码：")
        print(f"   红球：{' '.join(map(str, red_numbers))}")
        print(f"   蓝球：{blue_number}")
        print(f"   策略：红球(2热:{selected_hot} + 2温:{selected_warm} + 2冷:{selected_cold}) | 蓝球(热门:{blue_number})")
        print(f"   分析期数：最近30期")
        
        return red_numbers, blue_number
    
    def recommend_pl5_numbers(self):
        """推荐排列五号码"""
        if self.pl5_df is None:
            return None
            
        print("\n=== 排列五号码推荐 ===")
        
        # 检查是否有数据
        if len(self.pl5_df) == 0:
            print("   警告：排列五数据为空")
            return None
        
        # 获取最近30期数据
        recent_data = self.pl5_df.tail(30)
        
        # 为每个位置推荐数字
        recommended_numbers = []
        recommendation_strategy = []
        
        for i, col in enumerate(self.pl5_cols):
            if col not in recent_data.columns:
                # 如果没有单独的列，尝试从开奖号码提取
                if '开奖号码' in recent_data.columns:
                    recent_data[col] = recent_data['开奖号码'].astype(str).str.zfill(5).str[i]
            
            if col in recent_data.columns:
                numbers = recent_data[col].astype(int)
                freq = numbers.value_counts()
                
                # 分析奇偶、大小分布
                odd_count = (numbers % 2 == 1).sum()
                even_count = (numbers % 2 == 0).sum()
                small_count = (numbers <= 4).sum()
                big_count = (numbers >= 5).sum()
                
                # 推荐策略：基于热号、冷号、奇偶、大小平衡
                # 1. 考虑热号（最近30期出现次数最多的）
                hot_numbers = freq.head(3).index.tolist()
                
                # 2. 考虑冷号（最近30期出现次数最少的或未出现的）
                cold_numbers = [num for num in range(0, 10) if num not in freq.index]
                if len(cold_numbers) < 2:
                    cold_numbers = freq.tail(3).index.tolist()
                
                # 3. 根据奇偶平衡推荐
                if odd_count > even_count:
                    # 最近奇数多，这次推荐偶数
                    parity_preference = [num for num in range(0, 10) if num % 2 == 0]
                else:
                    # 最近偶数多，这次推荐奇数
                    parity_preference = [num for num in range(0, 10) if num % 2 == 1]
                
                # 4. 根据大小平衡推荐
                if small_count > big_count:
                    # 最近小数多，这次推荐大数
                    size_preference = [num for num in range(5, 10)]
                else:
                    # 最近大数多，这次推荐小数
                    size_preference = [num for num in range(0, 5)]
                
                # 综合推荐：优先选择同时满足多个条件的数字
                preferred_numbers = []
                
                # 首先找同时满足奇偶和大小偏好的热号
                for num in hot_numbers:
                    if num in parity_preference and num in size_preference:
                        preferred_numbers.append(num)
                
                # 如果找不到，放宽条件
                if not preferred_numbers:
                    for num in hot_numbers:
                        if num in parity_preference or num in size_preference:
                            preferred_numbers.append(num)
                
                # 如果还是没有，从冷号中找满足条件的
                if not preferred_numbers:
                    for num in cold_numbers:
                        if num in parity_preference and num in size_preference:
                            preferred_numbers.append(num)
                
                # 如果还是没有，随机选择
                if not preferred_numbers:
                    if hot_numbers:
                        preferred_numbers = hot_numbers
                    else:
                        preferred_numbers = list(range(0, 10))
                
                # 从符合条件的数字中随机选择一个
                recommended_num = random.choice(preferred_numbers)
                recommended_numbers.append(recommended_num)
                
                # 记录推荐策略
                strategy_desc = f"{col}:"
                if recommended_num in hot_numbers:
                    strategy_desc += "热号"
                elif recommended_num in cold_numbers:
                    strategy_desc += "冷号"
                
                if recommended_num % 2 == 1:
                    strategy_desc += "+奇数"
                else:
                    strategy_desc += "+偶数"
                
                if recommended_num <= 4:
                    strategy_desc += "+小数"
                else:
                    strategy_desc += "+大数"
                
                recommendation_strategy.append(strategy_desc)
        
        print(f"🎯 推荐号码：{''.join(map(str, recommended_numbers))}")
        print(f"   策略：{' | '.join(recommendation_strategy)}")
        print(f"   分析期数：最近30期")
        
        return recommended_numbers
    
    def generate_report(self, validation_results, dlt_analysis, ssq_analysis, pl5_analysis, 
                       dlt_recommendation, ssq_recommendation, pl5_recommendation):
        """生成HTML报告"""
        print("\n=== 生成分析报告 ===")
        
        # 不需要生成图表
        plot_base64 = ""
        
        # 获取最新开奖信息
        latest_info = self.get_latest_draw_info()
        
        # 生成HTML内容
        html_content = self._create_html_content(
            plot_base64, validation_results,
            dlt_analysis, ssq_analysis, pl5_analysis,
            dlt_recommendation, ssq_recommendation, pl5_recommendation, 
            latest_info
        )
        
        # 保存报告 - 使用固定文件名
        report_path = "deepseek_cp_report.html"
        
        with open(report_path, 'w', encoding='utf-8') as f:
            f.write(html_content)
        
        print(f"✓ 报告已生成：{os.path.abspath(report_path)}")
        
        return report_path
    
    def _create_html_content(self, plot_base64, validation_results, 
                           dlt_analysis, ssq_analysis, pl5_analysis,
                           dlt_recommendation, ssq_recommendation, pl5_recommendation, latest_info):
        """创建HTML内容 - 优化移动端显示"""
        
        # 内部安全获取第一个元素的函数
        def safe_first(lst, default="N/A"):
            """安全获取列表的第一个元素"""
            if lst and len(lst) > 0:
                return lst[0]
            return default
        
        # 获取统计数据
        dlt_periods = len(self.dlt_df) if self.dlt_df is not None else 0
        ssq_periods = len(self.ssq_df) if self.ssq_df is not None else 0
        pl5_periods = len(self.pl5_df) if self.pl5_df is not None else 0
        
        # 大乐透推荐号码
        dlt_front_nums, dlt_back_nums = dlt_recommendation if dlt_recommendation else ([], [])
        
        # 双色球推荐号码
        ssq_red_nums, ssq_blue_num = ssq_recommendation if ssq_recommendation else ([], "")
        
        # 排列五推荐号码
        pl5_nums = pl5_recommendation if pl5_recommendation else []
        
        # 最新开奖信息
        dlt_latest = latest_info.get('dlt', {})
        ssq_latest = latest_info.get('ssq', {})
        pl5_latest = latest_info.get('pl5', {})
        
        # 获取昨天日期（用于显示）
        yesterday = (datetime.now() - timedelta(days=1)).strftime('%Y-%m-%d')
        
        # 处理数据可能为空的情况 - 使用安全函数
        dlt_hottest = safe_first(dlt_analysis.get('recent_front_hot', [])) if dlt_analysis else "N/A"
        dlt_coldest = safe_first(dlt_analysis.get('recent_front_cold', [])) if dlt_analysis else "N/A"
        dlt_back_hottest = safe_first(dlt_analysis.get('recent_back_hot', [])) if dlt_analysis else "N/A"
        dlt_back_coldest = safe_first(dlt_analysis.get('recent_back_cold', [])) if dlt_analysis else "N/A"
        
        ssq_red_hottest = safe_first(ssq_analysis.get('recent_red_hot', [])) if ssq_analysis else "N/A"
        ssq_red_coldest = safe_first(ssq_analysis.get('recent_red_cold', [])) if ssq_analysis else "N/A"
        ssq_blue_hottest = safe_first(ssq_analysis.get('recent_blue_hot', [])) if ssq_analysis else "N/A"
        ssq_blue_coldest = safe_first(ssq_analysis.get('recent_blue_cold', [])) if ssq_analysis else "N/A"
        
        # 排列五热门冷门信息
        pl5_hot_info = {}
        pl5_cold_info = {}
        if pl5_analysis and 'position_hot' in pl5_analysis:
            for pos, hot_list in pl5_analysis.get('position_hot', {}).items():
                pl5_hot_info[pos] = '、'.join(map(str, hot_list[:2])) if hot_list else "N/A"
            for pos, cold_list in pl5_analysis.get('position_cold', {}).items():
                pl5_cold_info[pos] = '、'.join(map(str, cold_list[:2])) if cold_list else "N/A"
        
        # 创建HTML内容，使用双重花括号转义
        html_template = '''<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>彩票数据分析报告（大乐透+双色球+排列五）</title>
    <style>
        * {{
            box-sizing: border-box;
            margin: 0;
            padding: 0;
        }}
        
        body {{
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "PingFang SC", "Microsoft YaHei", sans-serif;
            background-color: #F8F9FA;
            margin: 0;
            padding: 12px;
            color: #333;
            line-height: 1.6;
        }}
        
        .container {{
            max-width: 100%;
            margin: 0 auto;
        }}
        
        .header {{
            text-align: center;
            margin-bottom: 20px;
            padding: 20px 15px;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            border-radius: 12px;
            box-shadow: 0 4px 15px rgba(31,38,135,0.2);
        }}
        
        .header h1 {{
            font-size: 1.5rem;
            margin-bottom: 8px;
        }}
        
        .header p {{
            font-size: 0.9rem;
            opacity: 0.9;
        }}
        
        .section {{
            background-color: white;
            border-radius: 12px;
            padding: 20px 15px;
            margin-bottom: 20px;
            box-shadow: 0 2px 12px rgba(0,0,0,0.06);
        }}
        
        .section-title {{
            font-size: 1.2rem;
            font-weight: bold;
            margin-bottom: 15px;
            color: #667eea;
            display: flex;
            align-items: center;
            padding-bottom: 8px;
            border-bottom: 2px solid #f0f0f0;
        }}
        
        .lottery-grid {{
            display: flex;
            flex-direction: column;
            gap: 15px;
            margin: 15px 0;
        }}
        
        .lottery-card {{
            background: white;
            border-radius: 12px;
            padding: 18px;
            box-shadow: 0 2px 8px rgba(0,0,0,0.08);
            border-left: 4px solid;
            width: 100%;
        }}
        
        .dlt-card {{
            border-left-color: #667eea;
            min-height: 320px;  /* 统一卡片高度 */
            display: flex;
            flex-direction: column;
        }}
        
        .ssq-card {{
            border-left-color: #f5576c;
            min-height: 320px;  /* 统一卡片高度 */
            display: flex;
            flex-direction: column;
        }}
        
        .pl5-card {{
            border-left-color: #4facfe;
            min-height: 320px;  /* 统一卡片高度 */
            display: flex;
            flex-direction: column;
        }}
        
        .recommendation {{
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            border-radius: 12px;
            padding: 15px 12px;
            margin: 12px 0;
            flex-grow: 1;  /* 让推荐区域占据剩余空间 */
            display: flex;
            flex-direction: column;
            justify-content: center;
        }}
        
        .latest-draw {{
            background: linear-gradient(135deg, #4facfe 0%, #00f2fe 100%);
            color: white;
            border-radius: 12px;
            padding: 15px 12px;
            margin: 10px 0;
            min-height: 150px;  /* 统一高度 */
            display: flex;
            flex-direction: column;
            justify-content: center;
        }}
        
        .numbers {{
            font-size: 1.2rem;
            font-weight: bold;
            margin: 8px 0;
            text-align: center;
            letter-spacing: 1px;
            line-height: 1.6;
            white-space: nowrap;  /* 防止换行 */
            overflow: hidden;
            text-overflow: ellipsis;
        }}
        
        .pl5-numbers {{
            font-size: 1.8rem;
            font-weight: bold;
            margin: 10px 0;
            text-align: center;
            letter-spacing: 3px;
            color: #ff6b6b;
            line-height: 1.2;
            white-space: nowrap;  /* 防止换行 */
        }}
        
        .stats-grid {{
            display: grid;
            grid-template-columns: repeat(2, 1fr);
            gap: 12px;
            margin: 15px 0;
        }}
        
        .stat-card {{
            background: #f8f9fa;
            padding: 15px 10px;
            border-radius: 10px;
            text-align: center;
            border-left: 3px solid #667eea;
        }}
        
        .hot-number {{
            color: #ff6b6b;
            font-weight: bold;
        }}
        
        .cold-number {{
            color: #4facfe;
            font-weight: bold;
        }}
        
        .stat-value {{
            font-size: 1.3rem;
            font-weight: bold;
            color: #667eea;
            margin: 5px 0;
        }}
        
        .strategy-info {{
            background: #f0f8ff;
            border-radius: 10px;
            padding: 12px;
            margin: 10px 0;
            border-left: 3px solid #4facfe;
            font-size: 0.85rem;
        }}
        
        .strategy-info h4 {{
            margin-bottom: 6px;
            font-size: 0.9rem;
        }}
        
        .strategy-info ul {{
            padding-left: 18px;
            margin-top: 6px;
        }}
        
        .strategy-info li {{
            margin-bottom: 4px;
        }}
        
        .analysis-insight {{
            background: #f8f9fa;
            border-radius: 10px;
            padding: 15px;
            margin: 10px 0;
        }}
        
        .analysis-title {{
            font-size: 1rem;
            font-weight: bold;
            margin-bottom: 8px;
            color: #667eea;
        }}
        
        .update-time {{
            text-align: center;
            color: rgba(255,255,255,0.8);
            font-size: 0.8rem;
            margin-top: 8px;
        }}
        
        .footer {{
            text-align: center;
            margin-top: 30px;
            padding: 15px;
            color: #666;
            border-top: 1px solid #eee;
            font-size: 0.85rem;
        }}
        
        .footer-time {{
            color: #888;
            font-size: 0.8rem;
            margin-top: 8px;
        }}
        
        /* 平板和桌面端适配 */
        @media (min-width: 768px) {{
            body {{
                padding: 20px;
            }}
            
            .container {{
                max-width: 1200px;
            }}
            
            .header {{
                padding: 30px;
                margin-bottom: 30px;
            }}
            
            .header h1 {{
                font-size: 2rem;
            }}
            
            .section {{
                padding: 25px;
                margin-bottom: 25px;
            }}
            
            .lottery-grid {{
                flex-direction: row;
                gap: 20px;
            }}
            
            .lottery-card {{
                flex: 1;
            }}
            
            .stats-grid {{
                grid-template-columns: repeat(4, 1fr);
                gap: 15px;
            }}
            
            .numbers {{
                font-size: 1.4rem;
            }}
            
            .pl5-numbers {{
                font-size: 2.2rem;
                letter-spacing: 5px;
            }}
        }}
        
        /* 超小屏幕手机优化 */
        @media (max-width: 360px) {{
            body {{
                padding: 8px;
            }}
            
            .section {{
                padding: 15px 12px;
            }}
            
            .numbers {{
                font-size: 1rem;
                letter-spacing: 1px;
            }}
            
            .pl5-numbers {{
                font-size: 1.4rem;
                letter-spacing: 2px;
            }}
            
            .stat-card {{
                padding: 12px 8px;
            }}
            
            .stat-value {{
                font-size: 1.1rem;
            }}
            
            .strategy-info {{
                padding: 10px;
                font-size: 0.8rem;
            }}
        }}
    </style>
</head>
<body>
    <div class="container">
        <!-- 页眉 -->
        <div class="header">
            <h1>三彩票数据分析报告</h1>
            <p>基于历史数据的智能分析与号码推荐（大乐透+双色球+排列五）</p>
            <div class="update-time">最后更新：{update_time}</div>
        </div>
        
        <!-- 最新开奖信息 -->
        <div class="section">
            <div class="section-title">📅 最新开奖信息</div>
            <div class="lottery-grid">
                {dlt_latest_html}
                {ssq_latest_html}
                {pl5_latest_html}
            </div>
        </div>
        
        <!-- 数据概览 -->
        <div class="section">
            <div class="section-title">📊 数据概览</div>
            <div class="stats-grid">
                <div class="stat-card">
                    <div>大乐透期数</div>
                    <div class="stat-value">{dlt_periods}</div>
                    <div>历史数据</div>
                </div>
                <div class="stat-card">
                    <div>双色球期数</div>
                    <div class="stat-value">{ssq_periods}</div>
                    <div>历史数据</div>
                </div>
                <div class="stat-card">
                    <div>排列五期数</div>
                    <div class="stat-value">{pl5_periods}</div>
                    <div>历史数据</div>
                </div>
                <div class="stat-card">
                    <div>分析类型</div>
                    <div class="stat-value">{analysis_types}</div>
                    <div>彩票种类</div>
                </div>
            </div>
        </div>
        
        <!-- 号码推荐 -->
        <div class="section">
            <div class="section-title">🎯 智能号码推荐</div>
            <div class="lottery-grid">
                {dlt_recommendation_html}
                {ssq_recommendation_html}
                {pl5_recommendation_html}
            </div>
        </div>
        
        <!-- 核心发现 -->
        <div class="section">
            <div class="section-title">🔍 核心发现（基于最近30期数据）</div>
            <div class="lottery-grid">
                <div class="lottery-card">
                    <div class="analysis-title">🏀 大乐透热门与冷门号码</div>
                    <div class="analysis-insight">
                        <p><strong>前区热门号码：</strong><span class="hot-number">{dlt_front_hot_numbers}</span></p>
                        <p><strong>前区冷门号码：</strong><span class="cold-number">{dlt_front_cold_numbers}</span></p>
                        <p><strong>后区热门号码：</strong><span class="hot-number">{dlt_back_hot_numbers}</span></p>
                        <p><strong>后区冷门号码：</strong><span class="cold-number">{dlt_back_cold_numbers}</span></p>
                    </div>
                </div>
                <div class="lottery-card">
                    <div class="analysis-title">🔴 双色球热门与冷门号码</div>
                    <div class="analysis-insight">
                        <p><strong>红球热门号码：</strong><span class="hot-number">{ssq_red_hot_numbers}</span></p>
                        <p><strong>红球冷门号码：</strong><span class="cold-number">{ssq_red_cold_numbers}</span></p>
                        <p><strong>蓝球热门号码：</strong><span class="hot-number">{ssq_blue_hot_numbers}</span></p>
                        <p><strong>蓝球冷门号码：</strong><span class="cold-number">{ssq_blue_cold_numbers}</span></p>
                    </div>
                </div>
                <div class="lottery-card">
                    <div class="analysis-title">🔢 排列五热门与冷门号码</div>
                    <div class="analysis-insight">
                        <p><strong>万位热门数字：</strong><span class="hot-number">{pl5_wan_hot}</span> | <strong>冷门：</strong><span class="cold-number">{pl5_wan_cold}</span></p>
                        <p><strong>千位热门数字：</strong><span class="hot-number">{pl5_qian_hot}</span> | <strong>冷门：</strong><span class="cold-number">{pl5_qian_cold}</span></p>
                        <p><strong>百位热门数字：</strong><span class="hot-number">{pl5_bai_hot}</span> | <strong>冷门：</strong><span class="cold-number">{pl5_bai_cold}</span></p>
                        <p><strong>十位热门数字：</strong><span class="hot-number">{pl5_shi_hot}</span> | <strong>冷门：</strong><span class="cold-number">{pl5_shi_cold}</span></p>
                        <p><strong>个位热门数字：</strong><span class="hot-number">{pl5_ge_hot}</span> | <strong>冷门：</strong><span class="cold-number">{pl5_ge_cold}</span></p>
                    </div>
                </div>
            </div>
        </div>
        
        <!-- 温馨提示 -->
        <div class="section">
            <div class="section-title">💡 温馨提示</div>
            <div class="lottery-grid">
                <div class="lottery-card">
                    <h3>大乐透规则</h3>
                    <ul>
                        <li>前区号码：1-35，选择5个号码</li>
                        <li>后区号码：1-12，选择2个号码</li>
                        <li>每周一、三、六开奖</li>
                        <li>分析基于<b>最近30期</b>历史数据</li>
                    </ul>
                </div>
                <div class="lottery-card">
                    <h3>双色球规则</h3>
                    <ul>
                        <li>红球号码：1-33，选择6个号码</li>
                        <li>蓝球号码：1-16，选择1个号码</li>
                        <li>每周二、四、日开奖</li>
                        <li>分析基于<b>最近30期</b>历史数据</li>
                    </ul>
                </div>
                <div class="lottery-card">
                    <h3>排列五规则</h3>
                    <ul>
                        <li>每位号码：0-9，共5位</li>
                        <li>每天开奖（除休市外）</li>
                        <li>分析基于<b>最近30期</b>历史数据</li>
                        <li>考虑奇偶、大小、热冷号平衡</li>
                    </ul>
                </div>
            </div>
            <div class="recommendation" style="margin-top: 15px;">
                <h3 style="margin-bottom: 10px;">🎯 购彩建议</h3>
                <ul>
                    <li>本推荐基于<b>最近30期数据的热冷平衡策略</b>，更加科学合理</li>
                    <li>排列五推荐考虑每个位置的独立趋势与整体平衡</li>
                </ul>
            </div>
        </div>
        
        <!-- 页脚 -->
        <div class="footer">
            <p>数据来源：本地Excel文件 | 分析方法：热冷平衡分析 | 版本：彩票分析系统 v3.0</p>
            <div class="footer-time">报告生成时间：{current_time}</div>
        </div>
    </div>
</body>
</html>'''
        
        # 准备HTML模板变量
        current_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        update_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        analysis_types = sum([1 for v in validation_results.values() if v])
        
        # 大乐透最新开奖信息HTML
        if dlt_latest:
            dlt_latest_html = f'''
            <div class="lottery-card dlt-card">
                <h3>🏀 大乐透最新开奖</h3>
                <div class="latest-draw">
                    <div style="text-align: center; margin-bottom: 10px;">
                        <strong>{dlt_latest.get('period', '最新期')}</strong> | {dlt_latest.get('date', '最新开奖')}
                    </div>
                    <div class="numbers">
                        前区：{' '.join(map(str, dlt_latest.get('front_numbers', []))) if dlt_latest.get('front_numbers') else '暂无数据'}<br>
                        后区：{' '.join(map(str, dlt_latest.get('back_numbers', []))) if dlt_latest.get('back_numbers') else '暂无数据'}
                    </div>
                </div>
            </div>
            '''
        else:
            dlt_latest_html = '<div class="lottery-card"><p>大乐透最新开奖信息不可用</p></div>'
        
        # 双色球最新开奖信息HTML
        if ssq_latest:
            ssq_latest_html = f'''
            <div class="lottery-card ssq-card">
                <h3>🔴 双色球最新开奖</h3>
                <div class="latest-draw">
                    <div style="text-align: center; margin-bottom: 10px;">
                        <strong>{ssq_latest.get('period', '最新期')}</strong> | {ssq_latest.get('date', '最新开奖')}
                    </div>
                    <div class="numbers">
                        红球：{' '.join(map(str, ssq_latest.get('red_numbers', []))) if ssq_latest.get('red_numbers') else '暂无数据'}<br>
                        蓝球：{ssq_latest.get('blue_number', '暂无数据')}
                    </div>
                </div>
            </div>
            '''
        else:
            ssq_latest_html = '<div class="lottery-card"><p>双色球最新开奖信息不可用</p></div>'
        
        # 排列五最新开奖信息HTML
        if pl5_latest:
            pl5_numbers = pl5_latest.get('numbers', [])
            pl5_latest_html = f'''
            <div class="lottery-card pl5-card">
                <h3>🔢 排列五最新开奖</h3>
                <div class="latest-draw">
                    <div style="text-align: center; margin-bottom: 10px;">
                        <strong>{pl5_latest.get('period', '最新期')}</strong> | {pl5_latest.get('date', '最新开奖')}
                    </div>
                    <div class="pl5-numbers">
                        {''.join(map(str, pl5_numbers)) if pl5_numbers else '暂无数据'}
                    </div>
                    <div style="text-align: center; margin-top: 10px; font-size: 0.85rem;">
                        位置：{'万' + str(pl5_numbers[0]) if len(pl5_numbers) > 0 else ''}
                        {' | 千' + str(pl5_numbers[1]) if len(pl5_numbers) > 1 else ''}
                        {' | 百' + str(pl5_numbers[2]) if len(pl5_numbers) > 2 else ''}
                        {' | 十' + str(pl5_numbers[3]) if len(pl5_numbers) > 3 else ''}
                        {' | 个' + str(pl5_numbers[4]) if len(pl5_numbers) > 4 else ''}
                    </div>
                </div>
            </div>
            '''
        else:
            pl5_latest_html = '<div class="lottery-card"><p>排列五最新开奖信息不可用</p></div>'
        
        # 大乐透推荐HTML
        if dlt_recommendation:
            dlt_recommendation_html = f'''
            <div class="lottery-card dlt-card">
                <h3>🏀 大乐透推荐</h3>
                <div class="recommendation">
                    <div class="numbers">
                        前区：{' '.join(map(str, dlt_front_nums)) if dlt_front_nums else '暂无数据'}<br>
                        后区：{' '.join(map(str, dlt_back_nums)) if dlt_back_nums else '暂无数据'}
                    </div>
                </div>
                <div class="strategy-info">
                    <h4>推荐策略：</h4>
                    <ul>
                        <li>基于<b>最近30期</b>数据分析</li>
                        <li>前区：<b>2个热门号码 + 2个冷门号码 + 1个随机号码</b></li>
                        <li>后区：<b>1个热门号码 + 1个随机号码</b></li>
                        <li>结合热冷平衡，提高覆盖范围</li>
                    </ul>
                </div>
            </div>
            '''
        else:
            dlt_recommendation_html = '<div class="lottery-card"><p>大乐透数据不可用</p></div>'
        
        # 双色球推荐HTML
        if ssq_recommendation:
            ssq_recommendation_html = f'''
            <div class="lottery-card ssq-card">
                <h3>🔴 双色球推荐</h3>
                <div class="recommendation">
                    <div class="numbers">
                        红球：{' '.join(map(str, ssq_red_nums)) if ssq_red_nums else '暂无数据'}<br>
                        蓝球：{ssq_blue_num if ssq_blue_num else '暂无数据'}
                    </div>
                </div>
                <div class="strategy-info">
                    <h4>推荐策略：</h4>
                    <ul>
                        <li>基于<b>最近30期</b>数据分析</li>
                        <li>红球：<b>2个热门号码 + 2个温门号码 + 2个冷门号码</b></li>
                        <li>蓝球：<b>热门号码</b>优先</li>
                        <li>平衡热冷分布，优化号码组合</li>
                    </ul>
                </div>
            </div>
            '''
        else:
            ssq_recommendation_html = '<div class="lottery-card"><p>双色球数据不可用</p></div>'
        
        # 排列五推荐HTML
        if pl5_recommendation:
            pl5_recommendation_html = f'''
            <div class="lottery-card pl5-card">
                <h3>🔢 排列五推荐</h3>
                <div class="recommendation">
                    <div class="pl5-numbers">
                        {''.join(map(str, pl5_nums)) if pl5_nums else '暂无数据'}
                    </div>
                </div>
                <div class="strategy-info">
                    <h4>推荐策略：</h4>
                    <ul>
                        <li>基于<b>最近30期</b>数据分析</li>
                        <li>每个位置独立分析热号、冷号</li>
                        <li>考虑<b>奇偶平衡</b>和<b>大小平衡</b></li>
                        <li>优先选择满足多个条件的数字</li>
                        <li>综合热冷号与趋势分析</li>
                    </ul>
                </div>
            </div>
            '''
        else:
            pl5_recommendation_html = '<div class="lottery-card"><p>排列五数据不可用</p></div>'
        
        # 大乐透热门冷门号码 - 显示多个而不是单个
        if dlt_analysis:
            dlt_front_hot_list = dlt_analysis.get('recent_front_hot', [])
            dlt_front_cold_list = dlt_analysis.get('recent_front_cold', [])
            dlt_back_hot_list = dlt_analysis.get('recent_back_hot', [])
            dlt_back_cold_list = dlt_analysis.get('recent_back_cold', [])
            
            # 显示多个号码，用顿号分隔
            dlt_front_hot_numbers = '、'.join(map(str, dlt_front_hot_list[:3])) if dlt_front_hot_list else "N/A"
            dlt_front_cold_numbers = '、'.join(map(str, dlt_front_cold_list[:3])) if dlt_front_cold_list else "N/A"
            dlt_back_hot_numbers = '、'.join(map(str, dlt_back_hot_list[:2])) if dlt_back_hot_list else "N/A"
            dlt_back_cold_numbers = '、'.join(map(str, dlt_back_cold_list[:2])) if dlt_back_cold_list else "N/A"
        else:
            dlt_front_hot_numbers = "N/A"
            dlt_front_cold_numbers = "N/A"
            dlt_back_hot_numbers = "N/A"
            dlt_back_cold_numbers = "N/A"
        
        # 双色球热门冷门号码 - 显示多个而不是单个
        if ssq_analysis:
            ssq_red_hot_list = ssq_analysis.get('recent_red_hot', [])
            ssq_red_cold_list = ssq_analysis.get('recent_red_cold', [])
            ssq_blue_hot_list = ssq_analysis.get('recent_blue_hot', [])
            ssq_blue_cold_list = ssq_analysis.get('recent_blue_cold', [])
            
            # 显示多个号码，用顿号分隔
            ssq_red_hot_numbers = '、'.join(map(str, ssq_red_hot_list[:3])) if ssq_red_hot_list else "N/A"
            ssq_red_cold_numbers = '、'.join(map(str, ssq_red_cold_list[:3])) if ssq_red_cold_list else "N/A"
            ssq_blue_hot_numbers = '、'.join(map(str, ssq_blue_hot_list[:2])) if ssq_blue_hot_list else "N/A"
            ssq_blue_cold_numbers = '、'.join(map(str, ssq_blue_cold_list[:2])) if ssq_blue_cold_list else "N/A"
        else:
            ssq_red_hot_numbers = "N/A"
            ssq_red_cold_numbers = "N/A"
            ssq_blue_hot_numbers = "N/A"
            ssq_blue_cold_numbers = "N/A"
        
        # 排列五热门冷门号码
        pl5_wan_hot = pl5_hot_info.get('万位', 'N/A')
        pl5_wan_cold = pl5_cold_info.get('万位', 'N/A')
        pl5_qian_hot = pl5_hot_info.get('千位', 'N/A')
        pl5_qian_cold = pl5_cold_info.get('千位', 'N/A')
        pl5_bai_hot = pl5_hot_info.get('百位', 'N/A')
        pl5_bai_cold = pl5_cold_info.get('百位', 'N/A')
        pl5_shi_hot = pl5_hot_info.get('十位', 'N/A')
        pl5_shi_cold = pl5_cold_info.get('十位', 'N/A')
        pl5_ge_hot = pl5_hot_info.get('个位', 'N/A')
        pl5_ge_cold = pl5_cold_info.get('个位', 'N/A')
        
        # 格式化最终HTML
        html_content = html_template.format(
            update_time=update_time,
            dlt_latest_html=dlt_latest_html,
            ssq_latest_html=ssq_latest_html,
            pl5_latest_html=pl5_latest_html,
            dlt_periods=dlt_periods,
            ssq_periods=ssq_periods,
            pl5_periods=pl5_periods,
            analysis_types=analysis_types,
            dlt_recommendation_html=dlt_recommendation_html,
            ssq_recommendation_html=ssq_recommendation_html,
            pl5_recommendation_html=pl5_recommendation_html,
            dlt_front_hot_numbers=dlt_front_hot_numbers,
            dlt_front_cold_numbers=dlt_front_cold_numbers,
            dlt_back_hot_numbers=dlt_back_hot_numbers,
            dlt_back_cold_numbers=dlt_back_cold_numbers,
            ssq_red_hot_numbers=ssq_red_hot_numbers,
            ssq_red_cold_numbers=ssq_red_cold_numbers,
            ssq_blue_hot_numbers=ssq_blue_hot_numbers,
            ssq_blue_cold_numbers=ssq_blue_cold_numbers,
            pl5_wan_hot=pl5_wan_hot,
            pl5_wan_cold=pl5_wan_cold,
            pl5_qian_hot=pl5_qian_hot,
            pl5_qian_cold=pl5_qian_cold,
            pl5_bai_hot=pl5_bai_hot,
            pl5_bai_cold=pl5_bai_cold,
            pl5_shi_hot=pl5_shi_hot,
            pl5_shi_cold=pl5_shi_cold,
            pl5_ge_hot=pl5_ge_hot,
            pl5_ge_cold=pl5_ge_cold,
            current_time=current_time
        )
        
        return html_content


def main():
    """主函数"""
    # 获取脚本所在目录的绝对路径
    script_dir = os.path.dirname(os.path.abspath(__file__))
    
    # 构建数据文件路径 - 假设数据文件与脚本在同一目录下
    file_path = os.path.join(script_dir, "Tools.xlsx")
    
    print("=" * 60)
    print("          彩票数据分析系统")
    print("       (大乐透 + 双色球 + 排列五)")
    print("=" * 60)
    print(f"数据文件路径：{file_path}")
    
    # 创建分析器实例
    analyzer = LotteryAnalyzer(file_path)

    # 1. 数据验证
    validation_results = analyzer.validate_data()
    
    if not any(validation_results.values()):
        print("没有可用的彩票数据，程序退出")
        return  # 直接返回，程序结束
    
    # 2. 数据分析
    dlt_analysis = None
    ssq_analysis = None
    pl5_analysis = None
    
    if validation_results.get('dlt'):
        dlt_analysis = analyzer.analyze_dlt()
    
    if validation_results.get('ssq'):
        ssq_analysis = analyzer.analyze_ssq()
    
    if validation_results.get('pl5'):
        pl5_analysis = analyzer.analyze_pl5()
    
    # 3. 号码推荐
    dlt_recommendation = None
    ssq_recommendation = None
    pl5_recommendation = None
    
    if validation_results.get('dlt'):
        dlt_recommendation = analyzer.recommend_dlt_numbers()
    
    if validation_results.get('ssq'):
        ssq_recommendation = analyzer.recommend_ssq_numbers()
    
    if validation_results.get('pl5'):
        pl5_recommendation = analyzer.recommend_pl5_numbers()
    
    # 4. 生成报告
    report_path = analyzer.generate_report(
        validation_results, dlt_analysis, ssq_analysis, pl5_analysis,
        dlt_recommendation, ssq_recommendation, pl5_recommendation
    )
    
    print("\n" + "=" * 60)
    print("          分析完成！")
    print(f"          报告文件：{report_path}")
    print("=" * 60)
   
    
if __name__ == "__main__":
    main()