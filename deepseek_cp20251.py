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
from datetime import datetime
import random
import warnings

# 过滤matplotlib字体警告
warnings.filterwarnings("ignore", category=UserWarning)

class LotteryAnalyzer:
    def __init__(self, file_path):
        self.file_path = file_path
        self.dlt_df = None
        self.ssq_df = None
        
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
                return {'dlt': False, 'ssq': False}
            
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
            
            return results
            
        except Exception as e:
            print(f"✗ 读取文件失败：{str(e)}")
            return {'dlt': False, 'ssq': False}
    
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
        
        return latest_info
    
    def analyze_dlt(self):
        """分析大乐透数据"""
        if self.dlt_df is None:
            return None
            
        print("\n=== 大乐透数据分析 ===")
        
        front_numbers = pd.concat([self.dlt_df[col] for col in self.dlt_front_cols])
        back_numbers = pd.concat([self.dlt_df[col] for col in self.dlt_back_cols])
        
        # 频率统计
        front_freq = front_numbers.value_counts().sort_index()
        back_freq = back_numbers.value_counts().sort_index()
        
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
        
        print(f"   前区热门号码：{front_freq.head(3).index.tolist()}")
        print(f"   后区热门号码：{back_freq.head(3).index.tolist()}")
        print(f"   前区奇偶比：{front_odd}/{front_even} ({front_odd/len(front_numbers):.1%}:{front_even/len(front_numbers):.1%})")
        
        return {
            'front_numbers': front_numbers,
            'back_numbers': back_numbers,
            'front_freq': front_freq,
            'back_freq': back_freq,
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
        
        red_numbers = pd.concat([self.ssq_df[col] for col in self.ssq_red_cols])
        blue_numbers = pd.concat([self.ssq_df[col] for col in self.ssq_blue_cols])
        
        # 频率统计
        red_freq = red_numbers.value_counts().sort_index()
        blue_freq = blue_numbers.value_counts().sort_index()
        
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
        
        print(f"   红球热门号码：{red_freq.head(3).index.tolist()}")
        print(f"   蓝球热门号码：{blue_freq.head(3).index.tolist()}")
        print(f"   红球奇偶比：{red_odd}/{red_even} ({red_odd/len(red_numbers):.1%}:{red_even/len(red_numbers):.1%})")
        
        return {
            'red_numbers': red_numbers,
            'blue_numbers': blue_numbers,
            'red_freq': red_freq,
            'blue_freq': blue_freq,
            'red_odd': red_odd,
            'red_even': red_even,
            'blue_odd': blue_odd,
            'blue_even': blue_even,
            'red_intervals': red_intervals.value_counts(),
            'blue_intervals': blue_intervals.value_counts()
        }
    
    def recommend_dlt_numbers(self):
        """推荐大乐透号码 - 改进版"""
        if self.dlt_df is None:
            return None
            
        print("\n=== 大乐透号码推荐 ===")
        
        # 获取最近15期数据
        recent_data = self.dlt_df.tail(15)
        recent_front = pd.concat([recent_data[col] for col in self.dlt_front_cols])
        recent_back = pd.concat([recent_data[col] for col in self.dlt_back_cols])
        
        # 计算近期频率
        recent_front_freq = recent_front.value_counts()
        recent_back_freq = recent_back.value_counts()
        
        # 获取所有可能号码
        all_front = list(range(self.dlt_front_range[0], self.dlt_front_range[1] + 1))
        all_back = list(range(self.dlt_back_range[0], self.dlt_back_range[1] + 1))
        
        # 前区号码选择策略：2个热门 + 2个冷门 + 1个随机
        # 热门号码（最近15期出现次数最多的）
        front_hot = recent_front_freq.head(10).index.tolist()
        # 冷门号码（最近15期出现次数最少的，或未出现的）
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
        print(f"   分析期数：最近15期")
        
        return front_numbers, back_numbers
    
    def recommend_ssq_numbers(self):
        """推荐双色球号码 - 改进版"""
        if self.ssq_df is None:
            return None
            
        print("\n=== 双色球号码推荐 ===")
        
        # 获取最近15期数据
        recent_data = self.ssq_df.tail(15)
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
        print(f"   分析期数：最近15期")
        
        return red_numbers, blue_number
    
    def generate_plots(self, dlt_analysis, ssq_analysis):
        """生成可视化图表"""
        # 设置图表字体
        plt.rcParams['font.sans-serif'] = ['SimHei', 'Microsoft YaHei', 'DejaVu Sans']
        plt.rcParams['axes.unicode_minus'] = False
        
        fig = plt.figure(figsize=(20, 16))
        fig.patch.set_facecolor('#F8F9FA')
        
        # 配色方案
        colors = ['#667eea', '#764ba2', '#f093fb', '#f5576c', '#4facfe', '#00f2fe']
        
        if dlt_analysis:
            # 大乐透图表
            ax1 = plt.subplot(2, 3, 1)
            front_freq = dlt_analysis['front_freq']
            ax1.bar(front_freq.index, front_freq.values, color=colors[0], alpha=0.7)
            ax1.set_title('大乐透前区频率分布', fontsize=12, fontweight='bold')
            ax1.grid(alpha=0.2)
            
            ax2 = plt.subplot(2, 3, 2)
            back_freq = dlt_analysis['back_freq']
            ax2.bar(back_freq.index, back_freq.values, color=colors[1], alpha=0.7)
            ax2.set_title('大乐透后区频率分布', fontsize=12, fontweight='bold')
            ax2.grid(alpha=0.2)
            
            ax3 = plt.subplot(2, 3, 3)
            front_odd = dlt_analysis['front_odd']
            front_even = dlt_analysis['front_even']
            ax3.pie([front_odd, front_even], labels=['奇数', '偶数'], colors=[colors[2], colors[3]], autopct='%1.1f%%')
            ax3.set_title('大乐透前区奇偶分布', fontsize=12, fontweight='bold')
        
        if ssq_analysis:
            # 双色球图表
            ax4 = plt.subplot(2, 3, 4)
            red_freq = ssq_analysis['red_freq']
            ax4.bar(red_freq.index, red_freq.values, color=colors[0], alpha=0.7)
            ax4.set_title('双色球红球频率分布', fontsize=12, fontweight='bold')
            ax4.grid(alpha=0.2)
            
            ax5 = plt.subplot(2, 3, 5)
            blue_freq = ssq_analysis['blue_freq']
            ax5.bar(blue_freq.index, blue_freq.values, color=colors[1], alpha=0.7)
            ax5.set_title('双色球蓝球频率分布', fontsize=12, fontweight='bold')
            ax5.grid(alpha=0.2)
            
            ax6 = plt.subplot(2, 3, 6)
            red_odd = ssq_analysis['red_odd']
            red_even = ssq_analysis['red_even']
            ax6.pie([red_odd, red_even], labels=['奇数', '偶数'], colors=[colors[2], colors[3]], autopct='%1.1f%%')
            ax6.set_title('双色球红球奇偶分布', fontsize=12, fontweight='bold')
        
        plt.tight_layout()
        
        # 转换为base64
        buffer = BytesIO()
        plt.savefig(buffer, format='png', dpi=100, bbox_inches='tight', facecolor='#F8F9FA')
        buffer.seek(0)
        img_base64 = base64.b64encode(buffer.getvalue()).decode()
        plt.close()
        
        return img_base64
    
    def generate_report(self, validation_results, dlt_analysis, ssq_analysis, dlt_recommendation, ssq_recommendation):
        """生成HTML报告"""
        print("\n=== 生成分析报告 ===")
        
        # 生成图表
        plot_base64 = self.generate_plots(dlt_analysis, ssq_analysis)
        
        # 获取最新开奖信息
        latest_info = self.get_latest_draw_info()
        
        # 生成HTML内容
        html_content = self._create_html_content(
            plot_base64, validation_results,
            dlt_analysis, ssq_analysis, dlt_recommendation, ssq_recommendation, latest_info
        )
        
        # 保存报告 - 使用固定文件名
        report_path = "deepseek_cp_report.html"
        
        with open(report_path, 'w', encoding='utf-8') as f:
            f.write(html_content)
        
        print(f"✓ 报告已生成：{os.path.abspath(report_path)}")
        
        return report_path
    
    def _create_html_content(self, plot_base64, validation_results, 
                           dlt_analysis, ssq_analysis, dlt_recommendation, ssq_recommendation, latest_info):
        """创建HTML内容 - 优化移动端显示"""
        
        # 获取统计数据
        dlt_periods = len(self.dlt_df) if self.dlt_df is not None else 0
        ssq_periods = len(self.ssq_df) if self.ssq_df is not None else 0
        
        # 大乐透推荐号码
        dlt_front_nums, dlt_back_nums = dlt_recommendation if dlt_recommendation else ([], [])
        
        # 双色球推荐号码
        ssq_red_nums, ssq_blue_num = ssq_recommendation if ssq_recommendation else ([], "")
        
        # 最新开奖信息
        dlt_latest = latest_info.get('dlt', {})
        ssq_latest = latest_info.get('ssq', {})
        
        html_content = f"""
<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>彩票数据分析报告</title>
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
        }}
        
        .ssq-card {{
            border-left-color: #f5576c;
        }}
        
        .recommendation {{
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            border-radius: 12px;
            padding: 20px;
            margin: 15px 0;
        }}
        
        .latest-draw {{
            background: linear-gradient(135deg, #4facfe 0%, #00f2fe 100%);
            color: white;
            border-radius: 12px;
            padding: 18px;
            margin: 12px 0;
        }}
        
        .numbers {{
            font-size: 1.3rem;
            font-weight: bold;
            margin: 12px 0;
            text-align: center;
            letter-spacing: 2px;
            line-height: 1.8;
        }}
        
        .chart-container {{
            background-color: rgba(255,255,255,0.9);
            border-radius: 10px;
            padding: 15px;
            margin: 15px 0;
            text-align: center;
            overflow: hidden;
        }}
        
        .chart-container img {{
            max-width: 100%;
            height: auto;
            border-radius: 8px;
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
        
        .stat-value {{
            font-size: 1.3rem;
            font-weight: bold;
            color: #667eea;
            margin: 5px 0;
        }}
        
        .strategy-info {{
            background: #f0f8ff;
            border-radius: 10px;
            padding: 15px;
            margin: 12px 0;
            border-left: 3px solid #4facfe;
            font-size: 0.9rem;
        }}
        
        .strategy-info ul {{
            padding-left: 18px;
            margin-top: 8px;
        }}
        
        .strategy-info li {{
            margin-bottom: 6px;
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
                font-size: 1.8rem;
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
                font-size: 1.1rem;
                letter-spacing: 1px;
            }}
            
            .stat-card {{
                padding: 12px 8px;
            }}
            
            .stat-value {{
                font-size: 1.1rem;
            }}
        }}
    </style>
</head>
<body>
    <div class="container">
        <!-- 页眉 -->
        <div class="header">
            <h1>数据分析报告</h1>
            <p>基于历史数据的智能分析与号码推荐</p>
            <div class="update-time">最后更新：{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</div>
        </div>
        
        <!-- 最新开奖信息 -->
        <div class="section">
            <div class="section-title">📅 最新开奖信息</div>
            <div class="lottery-grid">
                {"".join(f'''
                <div class="lottery-card dlt-card">
                    <h3>🏀 大乐透最新开奖</h3>
                    <div class="latest-draw">
                        <div style="text-align: center; margin-bottom: 10px;">
                            <strong>{dlt_latest.get('period', '最新期')}</strong> | {dlt_latest.get('date', '最新开奖')}
                        </div>
                        <div class="numbers">
                            前区：{' '.join(map(str, dlt_latest.get('front_numbers', [])))}<br>
                            后区：{' '.join(map(str, dlt_latest.get('back_numbers', [])))}
                        </div>
                    </div>
                </div>
                ''' if dlt_latest else '<div class="lottery-card"><p>大乐透最新开奖信息不可用</p></div>')}
                
                {"".join(f'''
                <div class="lottery-card ssq-card">
                    <h3>🔴 双色球最新开奖</h3>
                    <div class="latest-draw">
                        <div style="text-align: center; margin-bottom: 10px;">
                            <strong>{ssq_latest.get('period', '最新期')}</strong> | {ssq_latest.get('date', '最新开奖')}
                        </div>
                        <div class="numbers">
                            红球：{' '.join(map(str, ssq_latest.get('red_numbers', [])))}<br>
                            蓝球：{ssq_latest.get('blue_number', '')}
                        </div>
                    </div>
                </div>
                ''' if ssq_latest else '<div class="lottery-card"><p>双色球最新开奖信息不可用</p></div>')}
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
                    <div>分析类型</div>
                    <div class="stat-value">{2 if validation_results.get('dlt') and validation_results.get('ssq') else 1}</div>
                    <div>彩票种类</div>
                </div>
                <div class="stat-card">
                    <div>数据状态</div>
                    <div class="stat-value">{
        "完整" if validation_results.get('dlt') and validation_results.get('ssq') 
        else "部分" if validation_results.get('dlt') or validation_results.get('ssq') 
        else "异常"
    }</div>
                    <div>验证结果</div>
                </div>
            </div>
        </div>
        
        <!-- 号码推荐 -->
        <div class="section">
            <div class="section-title">🎯 智能号码推荐</div>
            <div class="lottery-grid">
                {"".join(f'''
                <div class="lottery-card dlt-card">
                    <h3>🏀 大乐透推荐</h3>
                    <div class="recommendation">
                        <div class="numbers">
                            前区：{' '.join(map(str, dlt_front_nums))}<br>
                            后区：{' '.join(map(str, dlt_back_nums))}
                        </div>
                    </div>
                    <div class="strategy-info">
                        <h4>推荐策略：</h4>
                        <ul>
                            <li>基于<b>最近15期</b>数据分析</li>
                            <li>前区：<b>2个热门号码 + 2个冷门号码 + 1个随机号码</b></li>
                            <li>后区：<b>1个热门号码 + 1个随机号码</b></li>
                            <li>结合热冷平衡，提高覆盖范围</li>
                        </ul>
                    </div>
                </div>
                ''' if dlt_recommendation else '<div class="lottery-card"><p>大乐透数据不可用</p></div>')}
                
                {"".join(f'''
                <div class="lottery-card ssq-card">
                    <h3>🔴 双色球推荐</h3>
                    <div class="recommendation">
                        <div class="numbers">
                            红球：{' '.join(map(str, ssq_red_nums))}<br>
                            蓝球：{ssq_blue_num}
                        </div>
                    </div>
                    <div class="strategy-info">
                        <h4>推荐策略：</h4>
                        <ul>
                            <li>基于<b>最近15期</b>数据分析</li>
                            <li>红球：<b>2个热门号码 + 2个温门号码 + 2个冷门号码</b></li>
                            <li>蓝球：<b>热门号码</b>优先</li>
                            <li>平衡热冷分布，优化号码组合</li>
                        </ul>
                    </div>
                </div>
                ''' if ssq_recommendation else '<div class="lottery-card"><p>双色球数据不可用</p></div>')}
            </div>
        </div>
        
        <!-- 数据分析图表 -->
        <div class="section">
            <div class="section-title">📈 数据分析图表</div>
            <div class="chart-container">
                <img src="data:image/png;base64,{plot_base64}" alt="彩票分析图表">
            </div>
            <p style="text-align: center; margin-top: 10px; color: #666; font-size: 0.9rem;">
                上图展示了大乐透和双色球的号码频率分布以及奇偶分布情况，帮助理解历史号码的出现规律。
            </p>
        </div>
        
        <!-- 核心发现 -->
        <div class="section">
            <div class="section-title">🔍 核心发现</div>
            <div class="lottery-grid">
                {"".join(f'''
                <div class="lottery-card">
                    <h3>大乐透分析结果</h3>
                    <div class="stats-grid">
                        <div class="stat-card">
                            <div>前区最热</div>
                            <div class="stat-value">{dlt_analysis["front_freq"].index[0] if len(dlt_analysis["front_freq"]) > 0 else "N/A"}</div>
                            <div>号码</div>
                        </div>
                        <div class="stat-card">
                            <div>后区最热</div>
                            <div class="stat-value">{dlt_analysis["back_freq"].index[0] if len(dlt_analysis["back_freq"]) > 0 else "N/A"}</div>
                            <div>号码</div>
                        </div>
                        <div class="stat-card">
                            <div>前区奇偶</div>
                            <div class="stat-value">{dlt_analysis["front_odd"]}/{dlt_analysis["front_even"]}</div>
                            <div>奇数/偶数</div>
                        </div>
                        <div class="stat-card">
                            <div>数据期数</div>
                            <div class="stat-value">{dlt_periods}</div>
                            <div>分析基础</div>
                        </div>
                    </div>
                </div>
                ''' if dlt_analysis else '<div class="lottery-card"><p>大乐透分析不可用</p></div>')}
                
                {"".join(f'''
                <div class="lottery-card">
                    <h3>双色球分析结果</h3>
                    <div class="stats-grid">
                        <div class="stat-card">
                            <div>红球最热</div>
                            <div class="stat-value">{ssq_analysis["red_freq"].index[0] if len(ssq_analysis["red_freq"]) > 0 else "N/A"}</div>
                            <div>号码</div>
                        </div>
                        <div class="stat-card">
                            <div>蓝球最热</div>
                            <div class="stat-value">{ssq_analysis["blue_freq"].index[0] if len(ssq_analysis["blue_freq"]) > 0 else "N/A"}</div>
                            <div>号码</div>
                        </div>
                        <div class="stat-card">
                            <div>红球奇偶</div>
                            <div class="stat-value">{ssq_analysis["red_odd"]}/{ssq_analysis["red_even"]}</div>
                            <div>奇数/偶数</div>
                        </div>
                        <div class="stat-card">
                            <div>数据期数</div>
                            <div class="stat-value">{ssq_periods}</div>
                            <div>分析基础</div>
                        </div>
                    </div>
                </div>
                ''' if ssq_analysis else '<div class="lottery-card"><p>双色球分析不可用</p></div>')}
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
                        <li>分析基于<b>最近15期</b>历史数据</li>
                    </ul>
                </div>
                <div class="lottery-card">
                    <h3>双色球规则</h3>
                    <ul>
                        <li>红球号码：1-33，选择6个号码</li>
                        <li>蓝球号码：1-16，选择1个号码</li>
                        <li>每周二、四、日开奖</li>
                        <li>分析基于<b>最近15期</b>历史数据</li>
                    </ul>
                </div>
            </div>
            <div class="recommendation" style="margin-top: 15px;">
                <h3 style="margin-bottom: 10px;">🎯 购彩建议</h3>
                <ul>
                    <li>本推荐基于<b>最近15期数据的热冷平衡策略</b>，更加科学合理</li>
                    <li>彩票中奖号码是随机产生的，本推荐仅基于历史数据统计分析</li>
                    <li>请理性购彩，量力而行，享受游戏乐趣</li>
                    <li>建议结合个人幸运号码进行适当调整</li>
                    <li>数据分析结果仅供参考，不保证中奖</li>
                </ul>
            </div>
        </div>
        
        <!-- 页脚 -->
        <div class="footer">
            <p>数据来源：本地Excel文件 | 分析方法：热冷平衡分析 | 版本：双彩票分析系统 v2.0</p>
            <p>温馨提示：请理性购彩，未成年人不得购买彩票</p>
            <div class="footer-time">报告生成时间：{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</div>
        </div>
    </div>
</body>
</html>
"""
        return html_content

def main():
    """主函数"""
    # 获取脚本所在目录的绝对路径
    script_dir = os.path.dirname(os.path.abspath(__file__))
    
    # 构建数据文件路径 - 假设数据文件与脚本在同一目录下
    file_path = os.path.join(script_dir, "Tools.xlsx")
    
    print("=" * 60)
    print("          双彩票数据分析系统")
    print("         (大乐透 + 双色球)")
    print("=" * 60)
    print(f"数据文件路径：{file_path}")
    
    # 创建分析器实例
    analyzer = LotteryAnalyzer(file_path)
    
    # 1. 数据验证
    validation_results = analyzer.validate_data()
    
    if not any(validation_results.values()):
        print("没有可用的彩票数据，程序退出")
        input("程序执行完毕，按任意键退出...")
        return
    
    # 2. 数据分析
    dlt_analysis = None
    ssq_analysis = None
    
    if validation_results.get('dlt'):
        dlt_analysis = analyzer.analyze_dlt()
    
    if validation_results.get('ssq'):
        ssq_analysis = analyzer.analyze_ssq()
    
    # 3. 号码推荐
    dlt_recommendation = None
    ssq_recommendation = None
    
    if validation_results.get('dlt'):
        dlt_recommendation = analyzer.recommend_dlt_numbers()
    
    if validation_results.get('ssq'):
        ssq_recommendation = analyzer.recommend_ssq_numbers()
    
    # 4. 生成报告
    report_path = analyzer.generate_report(
        validation_results, dlt_analysis, ssq_analysis, 
        dlt_recommendation, ssq_recommendation
    )
    
    print("\n" + "=" * 60)
    print("          分析完成！")
    print(f"          报告文件：{report_path}")
    print("=" * 60)
    

if __name__ == "__main__":
    main()