import requests
from bs4 import BeautifulSoup
import pandas as pd
import re
import time
import random
from datetime import datetime
import os
from openpyxl import load_workbook
from tqdm import tqdm
from openpyxl.utils.dataframe import dataframe_to_rows
from openpyxl.worksheet.datavalidation import DataValidation
from openpyxl.worksheet.filters import FilterColumn, Filters
import json

class LotteryDataCrawler:
    def __init__(self):
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7',
            'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8',
            'Accept-Encoding': 'gzip, deflate, br',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1',
            'Cache-Control': 'max-age=0',
            'Sec-Fetch-Dest': 'document',
            'Sec-Fetch-Mode': 'navigate',
            'Sec-Fetch-Site': 'none',
            'Sec-Fetch-User': '?1',
        }
        self.session = requests.Session()
        self.session.headers.update(self.headers)
        
        # 添加重试机制
        from requests.adapters import HTTPAdapter
        from requests.packages.urllib3.util.retry import Retry
        
        retry_strategy = Retry(
            total=3,
            backoff_factor=1,
            status_forcelist=[429, 500, 502, 503, 504],
        )
        adapter = HTTPAdapter(max_retries=retry_strategy)
        self.session.mount("http://", adapter)
        self.session.mount("https://", adapter)

    # 大乐透函数（保持不变）
    def get_dlt_history_data_all(self):
        """
        获取所有大乐透历史开奖数据
        """
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
        }
        
        url = "https://datachart.500.com/dlt/history/history.shtml"
        
        try:
            response = requests.get(url, headers=headers, timeout=30)
            response.encoding = 'gb2312'
            
            soup = BeautifulSoup(response.text, 'html.parser')
            table = soup.find('table', {'id': 'tablelist'})
            
            if not table:
                return None
            
            data = []
            rows = table.find_all('tr')[2:]
            
            for row in rows:
                cols = row.find_all('td')
                if len(cols) < 15:
                    continue
                    
                period = cols[0].text.strip()
                front_nums = [cols[i].text.strip().zfill(2) for i in range(1, 6)]
                back_nums = [cols[i].text.strip().zfill(2) for i in range(6, 8)]
                prize_pool = cols[8].text.strip()
                first_prize_count = cols[9].text.strip()
                first_prize_amount = cols[10].text.strip()
                second_prize_count = cols[11].text.strip()
                second_prize_amount = cols[12].text.strip()
                total_bet = cols[13].text.strip()
                date = cols[14].text.strip()
                
                data.append([
                    period, 
                    front_nums[0], front_nums[1], front_nums[2], front_nums[3], front_nums[4],
                    back_nums[0], back_nums[1],
                    prize_pool, 
                    first_prize_count, 
                    first_prize_amount, 
                    second_prize_count, 
                    second_prize_amount, 
                    total_bet, 
                    date
                ])
            
            columns = [
                '期号', '前区1', '前区2', '前区3', '前区4', '前区5', '后区1', '后区2',
                '奖池奖金(元)', 
                '一等奖注数', '一等奖奖金(元)', '二等奖注数', '二等奖奖金(元)', 
                '总投注额(元)', '开奖日期'
            ]
            
            df = pd.DataFrame(data, columns=columns)
            df['开奖日期'] = pd.to_datetime(df['开奖日期'])
            df = df.sort_values(by='开奖日期', ascending=True)
            df = df.reset_index(drop=True)
            
            for col in ['期号', '前区1', '前区2', '前区3', '前区4', '前区5', '后区1', '后区2']:
                df[col] = df[col].astype(str)
            
            df['开奖日期'] = df['开奖日期'].dt.strftime('%Y-%m-%d')
            
            return df
            
        except Exception:
            return None

    def get_dlt_history_data_by_range(self, start_period, end_period):
        """
        按期号范围获取大乐透历史开奖数据
        """
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
        }
        
        url = f"https://datachart.500.com/dlt/history/newinc/history.php?start={start_period}&end={end_period}"
        
        try:
            response = requests.get(url, headers=headers, timeout=30)
            response.encoding = 'gb2312'
            
            soup = BeautifulSoup(response.text, 'html.parser')
            table = soup.find('table', {'id': 'tablelist'})
            
            if not table:
                return None
            
            data = []
            rows = table.find_all('tr')[2:]
            
            for row in rows:
                cols = row.find_all('td')
                if len(cols) < 15:
                    continue
                    
                period = cols[0].text.strip()
                front_nums = [cols[i].text.strip().zfill(2) for i in range(1, 6)]
                back_nums = [cols[i].text.strip().zfill(2) for i in range(6, 8)]
                prize_pool = cols[8].text.strip()
                first_prize_count = cols[9].text.strip()
                first_prize_amount = cols[10].text.strip()
                second_prize_count = cols[11].text.strip()
                second_prize_amount = cols[12].text.strip()
                total_bet = cols[13].text.strip()
                date = cols[14].text.strip()
                
                data.append([
                    period, 
                    front_nums[0], front_nums[1], front_nums[2], front_nums[3], front_nums[4],
                    back_nums[0], back_nums[1],
                    prize_pool, 
                    first_prize_count, 
                    first_prize_amount, 
                    second_prize_count, 
                    second_prize_amount, 
                    total_bet, 
                date
                ])
            
            columns = [
                '期号', '前区1', '前区2', '前区3', '前区4', '前区5', '后区1', '后区2',
                '奖池奖金(元)', 
                '一等奖注数', '一等奖奖金(元)', '二等奖注数', '二等奖奖金(元)', 
                '总投注额(元)', '开奖日期'
            ]
            
            df = pd.DataFrame(data, columns=columns)
            df['开奖日期'] = pd.to_datetime(df['开奖日期'])
            df = df.sort_values(by='开奖日期', ascending=True)
            df = df.reset_index(drop=True)
            
            for col in ['期号', '前区1', '前区2', '前区3', '前区4', '前区5', '后区1', '后区2']:
                df[col] = df[col].astype(str)
            
            df['开奖日期'] = df['开奖日期'].dt.strftime('%Y-%m-%d')
            
            return df
            
        except Exception:
            return None

    def get_all_dlt_history(self):
        """
        获取所有大乐透历史数据，分批获取然后合并
        """
        all_data = self.get_dlt_history_data_all()
        
        if all_data is not None and len(all_data) > 2700:
            return all_data
        
        # 分批获取数据
        all_data = pd.DataFrame()
        
        batches = [
            (1, 1000),
            (1001, 2000),
            (2001, 3000),
            (3001, 4000),
            (4001, 5000),
            (5001, 6000),
            (6001, 7000),
            (7001, 8000),
            (8001, 9000),
            (9001, 10000),
            (10001, 11000),
            (11001, 12000),
            (12001, 13000),
            (13001, 14000),
            (14001, 15000),
            (15001, 16000),
            (16001, 17000),
            (17001, 18000),
            (18001, 19000),
            (19001, 20000),
            (20001, 21000),
            (21001, 22000),
            (22001, 23000),
            (23001, 24000),
            (24001, 25000),
            (25001, 26000),
            (26001, 27000),
            (27001, 28000),
            (28001, 29000),
            (29001, 30000)
        ]
        
        # 使用进度条显示获取进度
        for start, end in tqdm(batches, desc="获取大乐透历史数据"):
            batch_data = self.get_dlt_history_data_by_range(start, end)
            
            if batch_data is not None and len(batch_data) > 0:
                all_data = pd.concat([all_data, batch_data], ignore_index=True)
            
            time.sleep(random.uniform(1, 3))
        
        if not all_data.empty:
            all_data['开奖日期'] = pd.to_datetime(all_data['开奖日期'])
            all_data = all_data.sort_values(by='开奖日期', ascending=True)
            all_data = all_data.reset_index(drop=True)
            
            for col in ['期号', '前区1', '前区2', '前区3', '前区4', '前区5', '后区1', '后区2']:
                all_data[col] = all_data[col].astype(str)
            
            all_data['开奖日期'] = all_data['开奖日期'].dt.strftime('%Y-%m-%d')
        
        return all_data

    def get_latest_dlt_data(self):
        """
        获取最新的大乐透开奖数据
        """
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
        }
        
        url = "https://datachart.500.com/dlt/history/newinc/history.php?start=00001&end=99999"
        
        try:
            response = requests.get(url, headers=headers, timeout=30)
            response.encoding = 'gb2312'
            
            soup = BeautifulSoup(response.text, 'html.parser')
            table = soup.find('table', {'id': 'tablelist'})
            
            if not table:
                return None
            
            data = []
            rows = table.find_all('tr')[2:]
            
            for row in rows:
                cols = row.find_all('td')
                if len(cols) < 15:
                    continue
                    
                period = cols[0].text.strip()
                front_nums = [cols[i].text.strip().zfill(2) for i in range(1, 6)]
                back_nums = [cols[i].text.strip().zfill(2) for i in range(6, 8)]
                prize_pool = cols[8].text.strip()
                first_prize_count = cols[9].text.strip()
                first_prize_amount = cols[10].text.strip()
                second_prize_count = cols[11].text.strip()
                second_prize_amount = cols[12].text.strip()
                total_bet = cols[13].text.strip()
                date = cols[14].text.strip()
                
                data.append([
                    period, 
                    front_nums[0], front_nums[1], front_nums[2], front_nums[3], front_nums[4],
                    back_nums[0], back_nums[1],
                    prize_pool, 
                    first_prize_count, 
                    first_prize_amount, 
                    second_prize_count, 
                    second_prize_amount, 
                    total_bet, 
                    date
                ])
            
            columns = [
                '期号', '前区1', '前区2', '前区3', '前区4', '前区5', '后区1', '后区2',
                '奖池奖金(元)', 
                '一等奖注数', '一等奖奖金(元)', '二等奖注数', '二等奖奖金(元)', 
                '总投注额(元)', '开奖日期'
            ]
            
            df = pd.DataFrame(data, columns=columns)
            df['开奖日期'] = pd.to_datetime(df['开奖日期'])
            df = df.sort_values(by='开奖日期', ascending=True)
            df = df.reset_index(drop=True)
            
            for col in ['期号', '前区1', '前区2', '前区3', '前区4', '前区5', '后区1', '后区2']:
                df[col] = df[col].astype(str)
            
            df['开奖日期'] = df['开奖日期'].dt.strftime('%Y-%m-%d')
            
            return df
            
        except Exception:
            return None

    # 双色球函数（保持不变）
    def get_ssq_history_data_all(self):
        """
        获取所有双色球历史开奖数据
        """
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
        }
        
        url = "https://datachart.500.com/ssq/history/history.shtml"
        
        try:
            response = requests.get(url, headers=headers, timeout=30)
            response.encoding = 'gb2312'
            
            soup = BeautifulSoup(response.text, 'html.parser')
            table = soup.find('table', {'id': 'tablelist'})
            
            if not table:
                return None
            
            data = []
            rows = table.find_all('tr')[2:]
            
            for row in rows:
                cols = row.find_all('td')
                if len(cols) < 16:
                    continue
                    
                period = cols[0].text.strip()
                red_nums = [cols[i].text.strip().zfill(2) for i in range(1, 7)]
                blue_num = cols[7].text.strip().zfill(2)
                prize_pool = cols[9].text.strip()
                first_prize_count = cols[10].text.strip()
                first_prize_amount = cols[11].text.strip()
                second_prize_count = cols[12].text.strip()
                second_prize_amount = cols[13].text.strip()
                total_bet = cols[14].text.strip()
                date = cols[15].text.strip()
                
                data.append([
                    period, 
                    red_nums[0], red_nums[1], red_nums[2], red_nums[3], red_nums[4], red_nums[5],
                    blue_num,
                    prize_pool, 
                    first_prize_count, 
                    first_prize_amount, 
                    second_prize_count, 
                    second_prize_amount, 
                    total_bet, 
                    date
                ])
            
            columns = [
                '期号', '红球1', '红球2', '红球3', '红球4', '红球5', '红球6', '蓝球',
                '奖池奖金(元)', 
                '一等奖注数', '一等奖奖金(元)', '二等奖注数', '二等奖奖金(元)', 
                '总投注额(元)', '开奖日期'
            ]
            
            df = pd.DataFrame(data, columns=columns)
            df['开奖日期'] = pd.to_datetime(df['开奖日期'])
            df = df.sort_values(by='开奖日期', ascending=True)
            df = df.reset_index(drop=True)
            
            for col in ['期号', '红球1', '红球2', '红球3', '红球4', '红球5', '红球6', '蓝球']:
                df[col] = df[col].astype(str)
            
            df['开奖日期'] = df['开奖日期'].dt.strftime('%Y-%m-%d')
            
            return df
            
        except Exception:
            return None

    def get_ssq_history_data_by_range(self, start_period, end_period):
        """
        按期号范围获取双色球历史开奖数据
        """
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
        }
        
        url = f"https://datachart.500.com/ssq/history/newinc/history.php?start={start_period}&end={end_period}"
        
        try:
            response = requests.get(url, headers=headers, timeout=30)
            response.encoding = 'gb2312'
            
            soup = BeautifulSoup(response.text, 'html.parser')
            table = soup.find('table', {'id': 'tablelist'})
            
            if not table:
                return None
            
            data = []
            rows = table.find_all('tr')[2:]
            
            for row in rows:
                cols = row.find_all('td')
                if len(cols) < 16:
                    continue
                    
                period = cols[0].text.strip()
                red_nums = [cols[i].text.strip().zfill(2) for i in range(1, 7)]
                blue_num = cols[7].text.strip().zfill(2)
                prize_pool = cols[9].text.strip()
                first_prize_count = cols[10].text.strip()
                first_prize_amount = cols[11].text.strip()
                second_prize_count = cols[12].text.strip()
                second_prize_amount = cols[13].text.strip()
                total_bet = cols[14].text.strip()
                date = cols[15].text.strip()
                
                data.append([
                    period, 
                    red_nums[0], red_nums[1], red_nums[2], red_nums[3], red_nums[4], red_nums[5],
                    blue_num,
                    prize_pool, 
                    first_prize_count, 
                    first_prize_amount, 
                    second_prize_count, 
                    second_prize_amount, 
                    total_bet, 
                    date
                ])
            
            columns = [
                '期号', '红球1', '红球2', '红球3', '红球4', '红球5', '红球6', '蓝球',
                '奖池奖金(元)', 
                '一等奖注数', '一等奖奖金(元)', '二等奖注数', '二等奖奖金(元)', 
                '总投注额(元)', '开奖日期'
            ]
            
            df = pd.DataFrame(data, columns=columns)
            df['开奖日期'] = pd.to_datetime(df['开奖日期'])
            df = df.sort_values(by='开奖日期', ascending=True)
            df = df.reset_index(drop=True)
            
            for col in ['期号', '红球1', '红球2', '红球3', '红球4', '红球5', '红球6', '蓝球']:
                df[col] = df[col].astype(str)
            
            df['开奖日期'] = df['开奖日期'].dt.strftime('%Y-%m-%d')
            
            return df
            
        except Exception:
            return None

    def get_all_ssq_history(self):
        """
        获取所有双色球历史数据，分批获取然后合并
        """
        all_data = self.get_ssq_history_data_all()
        
        if all_data is not None and len(all_data) > 2000:
            return all_data
        
        all_data = pd.DataFrame()
        
        batches = [
            (1, 1000),
            (1001, 2000),
            (2001, 3000),
            (3001, 4000),
            (4001, 5000),
            (5001, 6000),
            (6001, 7000),
            (7001, 8000),
            (8001, 9000),
            (9001, 10000),
            (10001, 11000),
            (11001, 12000),
            (12001, 13000),
            (13001, 14000),
            (14001, 15000),
            (15001, 16000),
            (16001, 17000),
            (17001, 18000),
            (18001, 19000),
            (19001, 20000),
            (20001, 21000),
            (21001, 22000),
            (22001, 23000),
            (23001, 24000),
            (24001, 25000),
            (25001, 26000)
        ]
        
        for start, end in tqdm(batches, desc="获取双色球历史数据"):
            batch_data = self.get_ssq_history_data_by_range(start, end)
            
            if batch_data is not None and len(batch_data) > 0:
                all_data = pd.concat([all_data, batch_data], ignore_index=True)
            
            time.sleep(random.uniform(1, 3))
        
        if not all_data.empty:
            all_data['开奖日期'] = pd.to_datetime(all_data['开奖日期'])
            all_data = all_data.sort_values(by='开奖日期', ascending=True)
            all_data = all_data.reset_index(drop=True)
            
            for col in ['期号', '红球1', '红球2', '红球3', '红球4', '红球5', '红球6', '蓝球']:
                all_data[col] = all_data[col].astype(str)
            
            all_data['开奖日期'] = all_data['开奖日期'].dt.strftime('%Y-%m-%d')
        
        return all_data

    def get_latest_ssq_data(self):
        """
        获取最新的双色球开奖数据
        """
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
        }
        
        url = "https://datachart.500.com/ssq/history/newinc/history.php?start=00001&end=99999"
        
        try:
            response = requests.get(url, headers=headers, timeout=30)
            response.encoding = 'gb2312'
            
            soup = BeautifulSoup(response.text, 'html.parser')
            table = soup.find('table', {'id': 'tablelist'})
            
            if not table:
                return None
            
            data = []
            rows = table.find_all('tr')[2:]
            
            for row in rows:
                cols = row.find_all('td')
                if len(cols) < 16:
                    continue
                    
                period = cols[0].text.strip()
                red_nums = [cols[i].text.strip().zfill(2) for i in range(1, 7)]
                blue_num = cols[7].text.strip().zfill(2)
                prize_pool = cols[9].text.strip()
                first_prize_count = cols[10].text.strip()
                first_prize_amount = cols[11].text.strip()
                second_prize_count = cols[12].text.strip()
                second_prize_amount = cols[13].text.strip()
                total_bet = cols[14].text.strip()
                date = cols[15].text.strip()
                
                data.append([
                    period, 
                    red_nums[0], red_nums[1], red_nums[2], red_nums[3], red_nums[4], red_nums[5],
                    blue_num,
                    prize_pool, 
                    first_prize_count, 
                    first_prize_amount, 
                    second_prize_count, 
                    second_prize_amount, 
                    total_bet, 
                    date
                ])
            
            columns = [
                '期号', '红球1', '红球2', '红球3', '红球4', '红球5', '红球6', '蓝球',
                '奖池奖金(元)', 
                '一等奖注数', '一等奖奖金(元)', '二等奖注数', '二等奖奖金(元)', 
                '总投注额(元)', '开奖日期'
            ]
            
            df = pd.DataFrame(data, columns=columns)
            df['开奖日期'] = pd.to_datetime(df['开奖日期'])
            df = df.sort_values(by='开奖日期', ascending=True)
            df = df.reset_index(drop=True)
            
            for col in ['期号', '红球1', '红球2', '红球3', '红球4', '红球5', '红球6', '蓝球']:
                df[col] = df[col].astype(str)
            
            df['开奖日期'] = df['开奖日期'].dt.strftime('%Y-%m-%d')
            
            return df
            
        except Exception:
            return None

    # 排列五和福彩3D函数（更新版）
    def get_pl5_recent_data(self, count=30):
        """
        获取排列五最近N期数据 - 改进版
        """
        print(f"开始获取排列五最近 {count} 期数据...")
        
        # 尝试多个URL
        urls = [
            "https://kaijiang.78500.cn/p5/",
            "https://www.78500.cn/p5/",
            "https://datachart.500.com/pl5/"
        ]
        
        for i, url in enumerate(urls):
            try:
                print(f"尝试连接 {url} (尝试 {i+1}/{len(urls)})...")
                response = self.session.get(url, timeout=20)
                print(f"响应状态码: {response.status_code}")
                
                # 尝试多种编码
                encodings = ['utf-8', 'gb2312', 'gbk', 'gb18030']
                content = None
                
                for encoding in encodings:
                    try:
                        response.encoding = encoding
                        content = response.text
                        print(f"使用编码 {encoding} 成功")
                        break
                    except UnicodeDecodeError:
                        continue
                
                if content is None:
                    print("所有编码尝试失败")
                    continue
                
                # 尝试解析
                df = self.parse_pl5_html(content)
                if df is not None and len(df) > 0:
                    print(f"成功获取到 {len(df)} 条排列五数据")
                    # 取最近count期数据
                    recent_df = df.head(count).copy()
                    # 按时间顺序排列（从早到晚）
                    recent_df = recent_df.sort_values('开奖日期', ascending=True).reset_index(drop=True)
                    return recent_df
                else:
                    print("解析数据为空")
                    
            except Exception as e:
                print(f"尝试 {url} 失败: {str(e)}")
                continue
        
        # 如果所有URL都失败，尝试备用方法
        print("主网站获取失败，尝试备用数据源...")
        return self.get_pl5_backup_data(count)

    def get_3d_recent_data(self, count=30):
        """
        获取福彩3D最近N期数据 - 改进版
        """
        print(f"开始获取福彩3D最近 {count} 期数据...")
        
        # 尝试多个URL
        urls = [
            "https://kaijiang.78500.cn/3d/",
            "https://www.78500.cn/3d/",
            "https://datachart.500.com/3d/"
        ]
        
        for i, url in enumerate(urls):
            try:
                print(f"尝试连接 {url} (尝试 {i+1}/{len(urls)})...")
                response = self.session.get(url, timeout=20)
                print(f"响应状态码: {response.status_code}")
                
                # 尝试多种编码
                encodings = ['utf-8', 'gb2312', 'gbk', 'gb18030']
                content = None
                
                for encoding in encodings:
                    try:
                        response.encoding = encoding
                        content = response.text
                        print(f"使用编码 {encoding} 成功")
                        break
                    except UnicodeDecodeError:
                        continue
                
                if content is None:
                    print("所有编码尝试失败")
                    continue
                
                df = self.parse_3d_html(content)
                if df is not None and len(df) > 0:
                    print(f"成功获取到 {len(df)} 条福彩3D数据")
                    # 取最近count期数据
                    recent_df = df.head(count).copy()
                    # 按时间顺序排列（从早到晚）
                    recent_df = recent_df.sort_values('开奖日期', ascending=True).reset_index(drop=True)
                    return recent_df
                else:
                    print("解析数据为空")
                    
            except Exception as e:
                print(f"尝试 {url} 失败: {str(e)}")
                continue
        
        # 如果所有URL都失败，尝试备用方法
        print("主网站获取失败，尝试备用数据源...")
        return self.get_3d_backup_data(count)
    
    def get_pl5_backup_data(self, count=30):
        """
        获取排列五备用数据源
        """
        print("尝试从备用数据源获取排列五数据...")
        try:
            # 尝试从中国福彩网获取
            url = "https://www.cwl.gov.cn/cwl_admin/front/cwlkj/search/kjxx/findDrawNotice"
            params = {
                'name': 'pl5',
                'issueCount': str(count),
                'issueStart': '',
                'issueEnd': '',
                'dayStart': '',
                'dayEnd': ''
            }
            
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
                'Accept': 'application/json, text/javascript, */*; q=0.01',
                'X-Requested-With': 'XMLHttpRequest',
                'Referer': 'https://www.cwl.gov.cn/'
            }
            
            response = requests.get(url, params=params, headers=headers, timeout=30, verify=False)
            print(f"备用数据源响应状态码: {response.status_code}")
            
            if response.status_code == 200:
                try:
                    data = response.json()
                    print(f"备用数据源返回数据: {data}")
                    
                    if data.get('state') == 0:
                        results = data.get('result', [])
                        data_list = []
                        for item in results:
                            numbers = item.get('red', '')
                            if numbers:
                                # 将号码格式化为带空格的格式
                                formatted_numbers = ' '.join(list(numbers))
                            else:
                                formatted_numbers = ''
                                
                            data_list.append({
                                '期号': item.get('code', ''),
                                '开奖日期': item.get('date', '').split(' ')[0] if item.get('date') else '',
                                '开奖号码': formatted_numbers,
                                '销售金额': item.get('sales', 0),
                                '一等奖注数': 0
                            })
                        
                        if data_list:
                            print(f"从备用数据源获取到 {len(data_list)} 条排列五数据")
                            df = pd.DataFrame(data_list)
                            return df
                except Exception as e:
                    print(f"解析备用数据源JSON失败: {str(e)}")
        except Exception as e:
            print(f"备用数据源获取失败: {str(e)}")
        
        return None
    
    def get_3d_backup_data(self, count=30):
        """
        获取福彩3D备用数据源
        """
        print("尝试从备用数据源获取福彩3D数据...")
        try:
            # 尝试从中国福彩网获取
            url = "https://www.cwl.gov.cn/cwl_admin/front/cwlkj/search/kjxx/findDrawNotice"
            params = {
                'name': '3d',
                'issueCount': str(count),
                'issueStart': '',
                'issueEnd': '',
                'dayStart': '',
                'dayEnd': ''
            }
            
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
                'Accept': 'application/json, text/javascript, */*; q=0.01',
                'X-Requested-With': 'XMLHttpRequest',
                'Referer': 'https://www.cwl.gov.cn/'
            }
            
            response = requests.get(url, params=params, headers=headers, timeout=30, verify=False)
            print(f"备用数据源响应状态码: {response.status_code}")
            
            if response.status_code == 200:
                try:
                    data = response.json()
                    print(f"备用数据源返回数据: {data}")
                    
                    if data.get('state') == 0:
                        results = data.get('result', [])
                        data_list = []
                        for item in results:
                            numbers = item.get('red', '')
                            if numbers:
                                # 将号码格式化为带空格的格式
                                formatted_numbers = ' '.join(list(numbers))
                            else:
                                formatted_numbers = ''
                                
                            data_list.append({
                                '期号': item.get('code', ''),
                                '开奖日期': item.get('date', '').split(' ')[0] if item.get('date') else '',
                                '开奖号码': formatted_numbers,
                                '销售金额': item.get('sales', 0)
                            })
                        
                        if data_list:
                            print(f"从备用数据源获取到 {len(data_list)} 条福彩3D数据")
                            df = pd.DataFrame(data_list)
                            return df
                except Exception as e:
                    print(f"解析备用数据源JSON失败: {str(e)}")
        except Exception as e:
            print(f"备用数据源获取失败: {str(e)}")
        
        return None
    
    def parse_pl5_html(self, html_content):
        """
        解析排列五HTML内容，提取开奖数据
        """
        soup = BeautifulSoup(html_content, 'html.parser')
        
        # 尝试不同的表格选择器
        tables = soup.find_all('table')
        
        data = []
        
        for table in tables:
            # 查找包含开奖数据的行
            rows = table.find_all('tr')
            for row in rows:
                cols = row.find_all('td')
                if len(cols) >= 4:  # 至少有期号、日期、销售金额、开奖号码
                    try:
                        # 提取期号
                        period = cols[0].get_text(strip=True)
                        if not period or not any(char.isdigit() for char in period):
                            continue
                        
                        # 提取开奖日期
                        date_text = cols[1].get_text(strip=True) if len(cols) > 1 else ''
                        
                        # 提取销售金额
                        sales_text = cols[2].get_text(strip=True) if len(cols) > 2 else '0'
                        sales_amount = self.parse_sales_amount(sales_text)
                        
                        # 提取开奖号码
                        number_cell = cols[3] if len(cols) > 3 else None
                        if number_cell:
                            # 尝试从链接获取
                            number_link = number_cell.find('a')
                            if number_link:
                                numbers = number_link.get_text(strip=True)
                            else:
                                numbers = number_cell.get_text(strip=True)
                        else:
                            numbers = ''
                        
                        # 清理号码格式
                        numbers = re.sub(r'\s+', ' ', numbers.strip())
                        clean_numbers = numbers.replace(' ', '')
                        
                        # 验证号码格式（应该是5位数字）
                        if not re.match(r'^\d{5}$', clean_numbers):
                            continue
                        
                        # 格式化号码（带空格）
                        if ' ' not in numbers and len(clean_numbers) == 5:
                            numbers = ' '.join(clean_numbers)
                        
                        # 提取一等奖信息（如果存在）
                        first_prize_count = 0
                        if len(cols) > 4:
                            first_prize_count = self.parse_prize_count(cols[4].get_text(strip=True))
                        
                        data.append({
                            '期号': period,
                            '开奖日期': date_text,
                            '销售金额': sales_amount,
                            '开奖号码': numbers,
                            '一等奖注数': first_prize_count
                        })
                        
                    except Exception as e:
                        continue
        
        return pd.DataFrame(data) if data else None
    
    def parse_3d_html(self, html_content):
        """
        解析福彩3D HTML内容，提取开奖数据
        """
        soup = BeautifulSoup(html_content, 'html.parser')
        
        # 尝试不同的表格选择器
        tables = soup.find_all('table')
        
        data = []
        
        for table in tables:
            # 查找包含开奖数据的行
            rows = table.find_all('tr')
            for row in rows:
                cols = row.find_all('td')
                if len(cols) >= 4:  # 至少有期号、日期、销售金额、开奖号码
                    try:
                        # 提取期号
                        period = cols[0].get_text(strip=True)
                        if not period or not any(char.isdigit() for char in period):
                            continue
                        
                        # 提取开奖日期
                        date_text = cols[1].get_text(strip=True) if len(cols) > 1 else ''
                        
                        # 提取销售金额
                        sales_text = cols[2].get_text(strip=True) if len(cols) > 2 else '0'
                        sales_amount = self.parse_sales_amount(sales_text)
                        
                        # 提取开奖号码
                        number_cell = cols[3] if len(cols) > 3 else None
                        if number_cell:
                            # 尝试从链接获取
                            number_link = number_cell.find('a')
                            if number_link:
                                numbers = number_link.get_text(strip=True)
                            else:
                                numbers = number_cell.get_text(strip=True)
                        else:
                            numbers = ''
                        
                        # 清理号码格式
                        numbers = re.sub(r'\s+', ' ', numbers.strip())
                        clean_numbers = numbers.replace(' ', '')
                        
                        # 验证号码格式（应该是3位数字）
                        if not re.match(r'^\d{3}$', clean_numbers):
                            continue
                        
                        # 格式化号码（带空格）
                        if ' ' not in numbers and len(clean_numbers) == 3:
                            numbers = ' '.join(clean_numbers)
                        
                        data.append({
                            '期号': period,
                            '开奖日期': date_text,
                            '销售金额': sales_amount,
                            '开奖号码': numbers
                        })
                        
                    except Exception as e:
                        continue
        
        return pd.DataFrame(data) if data else None
    
    def parse_sales_amount(self, text):
        """解析销售金额"""
        if not text or text in ['', '-', '0', 'N/A']:
            return 0
        try:
            # 移除逗号和单位
            text = text.replace(',', '').replace('元', '').replace('¥', '').strip()
            return int(float(text))
        except:
            return 0
    
    def parse_prize_count(self, text):
        """解析奖注数"""
        if not text or text in ['', '-']:
            return 0
        try:
            return int(text.replace(',', ''))
        except:
            return 0

# 通用函数（保持不变）
def get_existing_data(filename='Tools.xlsx', sheet_name='dltall'):
    """
    从Excel文件中读取现有的开奖数据
    """
    if not os.path.exists(filename):
        return pd.DataFrame()
    
    try:
        existing_df = pd.read_excel(filename, sheet_name=sheet_name, dtype=str)
        
        # 处理日期列，统一格式
        if '开奖日期' in existing_df.columns:
            existing_df['开奖日期'] = pd.to_datetime(existing_df['开奖日期'], errors='coerce').dt.strftime('%Y-%m-%d')
        
        if sheet_name == 'dltall':
            for col in ['期号', '前区1', '前区2', '前区3', '前区4', '前区5', '后区1', '后区2']:
                if col in existing_df.columns:
                    existing_df[col] = existing_df[col].astype(str).apply(lambda x: x.zfill(2) if x.isdigit() and len(x) == 1 else x)
        elif sheet_name == 'ssq':
            for col in ['期号', '红球1', '红球2', '红球3', '红球4', '红球5', '红球6', '蓝球']:
                if col in existing_df.columns:
                    existing_df[col] = existing_df[col].astype(str).apply(lambda x: x.zfill(2) if x.isdigit() and len(x) == 1 else x)
        
        return existing_df
    except Exception:
        return pd.DataFrame()

def safe_save_to_excel(df, filename='Tools.xlsx', sheet_name='dltall'):
    """安全保存数据，不修改现有文件结构，保留外部链接和其他工作表内容"""
    if df is None or len(df) == 0:
        return
        
    try:
        # 创建临时文件来保存新数据
        temp_filename = f"temp_{filename}"
        
        # 将数据保存到临时文件
        with pd.ExcelWriter(temp_filename, engine='openpyxl') as writer:
            df.to_excel(writer, sheet_name=sheet_name, index=False)
        
        # 加载原始文件和临时文件
        original_book = load_workbook(filename)
        temp_book = load_workbook(temp_filename)
        
        # 获取新数据
        temp_sheet = temp_book[sheet_name]
        new_data = []
        for row in temp_sheet.iter_rows(values_only=True):
            new_data.append(row)
        
        # 更新原始文件的工作表
        if sheet_name in original_book.sheetnames:
            original_sheet = original_book[sheet_name]
            
            # 清除旧数据（保留第一行标题）
            for row_idx in range(2, original_sheet.max_row + 1):
                for col_idx in range(1, original_sheet.max_column + 1):
                    original_sheet.cell(row=row_idx, column=col_idx).value = None
            
            # 写入新数据
            for row_idx, row_data in enumerate(new_data[1:], 2):  # 跳过标题行
                for col_idx, value in enumerate(row_data, 1):
                    if col_idx <= original_sheet.max_column:
                        original_sheet.cell(row=row_idx, column=col_idx, value=value)
        else:
            # 如果工作表不存在，创建新工作表
            original_sheet = original_book.create_sheet(sheet_name)
            # 写入所有数据（包括标题）
            for row_idx, row_data in enumerate(new_data, 1):
                for col_idx, value in enumerate(row_data, 1):
                    original_sheet.cell(row=row_idx, column=col_idx, value=value)
        
        original_book.save(filename)
        
        # 删除临时文件
        os.remove(temp_filename)
        
    except Exception:
        # 回退到原始方法
        try:
            if os.path.exists(filename):
                # 加载现有工作簿
                book = load_workbook(filename)
                
                # 如果工作表存在，则删除它（保留其他工作表）
                if sheet_name in book.sheetnames:
                    std = book[sheet_name]
                    book.remove(std)
                
                # 创建新工作表
                sheet = book.create_sheet(sheet_name)
                
                # 将数据写入工作表
                for r in dataframe_to_rows(df, index=False, header=True):
                    sheet.append(r)
                
                # 保存工作簿
                book.save(filename)
            else:
                # 文件不存在，创建新文件
                with pd.ExcelWriter(filename, engine='openpyxl') as writer:
                    df.to_excel(writer, sheet_name=sheet_name, index=False)
        except Exception:
            pass

def get_existing_dates(filename, sheet_name):
    """
    获取工作表中已存在的开奖日期
    """
    try:
        if not os.path.exists(filename):
            return set()
        
        # 读取现有数据
        existing_df = pd.read_excel(filename, sheet_name=sheet_name)
        
        # 如果数据为空，返回空集合
        if existing_df.empty or '开奖日期' not in existing_df.columns:
            return set()
        
        # 返回所有开奖日期的集合
        return set(existing_df['开奖日期'].astype(str))
    except Exception:
        return set()

def incremental_save_to_excel(new_df, filename='Tools.xlsx', sheet_name='pl5'):
    """
    增量保存数据到Excel，基于开奖日期去重
    """
    try:
        # 获取已存在的开奖日期
        existing_dates = get_existing_dates(filename, sheet_name)
        
        # 筛选出新数据（开奖日期不在现有数据中的行）
        new_rows = []
        for _, row in new_df.iterrows():
            if str(row['开奖日期']) not in existing_dates:
                new_rows.append(row)
        
        if not new_rows:
            return True
        
        # 创建新数据的DataFrame
        new_data_df = pd.DataFrame(new_rows)
        
        # 检查文件是否已存在
        if os.path.exists(filename):
            # 读取现有文件
            workbook = load_workbook(filename)
            
            # 检查工作表是否存在
            if sheet_name in workbook.sheetnames:
                # 读取现有数据
                existing_df = pd.read_excel(filename, sheet_name=sheet_name)
                
                # 合并新旧数据
                combined_df = pd.concat([existing_df, new_data_df], ignore_index=True)
                
                # 按开奖日期排序
                combined_df = combined_df.sort_values('开奖日期', ascending=True).reset_index(drop=True)
            else:
                # 工作表不存在，使用新数据
                combined_df = new_data_df
        else:
            # 文件不存在，创建新文件
            workbook = load_workbook()
            combined_df = new_data_df
        
        # 获取或创建工作表
        if sheet_name in workbook.sheetnames:
            worksheet = workbook[sheet_name]
        else:
            worksheet = workbook.create_sheet(sheet_name)
        
        # 清空工作表内容
        worksheet.delete_rows(1, worksheet.max_row)
        
        # 写入标题行
        headers = list(combined_df.columns)
        for col_idx, header in enumerate(headers, 1):
            worksheet.cell(row=1, column=col_idx, value=header)
        
        # 写入数据行
        for row_idx, row in enumerate(combined_df.itertuples(index=False), 2):
            for col_idx, value in enumerate(row, 1):
                worksheet.cell(row=row_idx, column=col_idx, value=value)
        
        # 设置冻结窗格（冻结第一行）
        worksheet.freeze_panes = 'A2'
        
        # 保存文件
        workbook.save(filename)
        workbook.close()
        
        return True
        
    except Exception:
        return False

def format_pl5_dataframe(df):
    """
    格式化排列五数据框
    """
    if df is None or len(df) == 0:
        return pd.DataFrame()
    
    # 确保列顺序正确
    expected_columns = ['期号', '开奖日期', '销售金额', '开奖号码', '一等奖注数']
    
    # 只保留需要的列
    available_columns = [col for col in expected_columns if col in df.columns]
    df = df[available_columns].copy()
    
    return df

def format_3d_dataframe(df):
    """
    格式化福彩3D数据框
    """
    if df is None or len(df) == 0:
        return pd.DataFrame()
    
    # 确保列顺序正确
    expected_columns = ['期号', '开奖日期', '销售金额', '开奖号码']
    
    # 只保留需要的列
    available_columns = [col for col in expected_columns if col in df.columns]
    df = df[available_columns].copy()
    
    return df

def update_ev_sheet_with_lottery_data(filename='Tools.xlsx'):
    """
    将pl5和3D工作表的开奖数据自动写入EV工作表的相应列
    只写入新数据，已存在的数据保持不变
    """
    try:
        if not os.path.exists(filename):
            print("文件不存在")
            return False
        
        # 加载工作簿
        workbook = load_workbook(filename)
        
        # 检查必要的工作表是否存在
        required_sheets = ['pl5', '3D', 'EV']
        for sheet in required_sheets:
            if sheet not in workbook.sheetnames:
                print(f"缺少必要的工作表: {sheet}")
                workbook.close()
                return False
        
        # 读取pl5数据
        pl5_df = pd.read_excel(filename, sheet_name='pl5')
        # 读取3D数据
        d3_df = pd.read_excel(filename, sheet_name='3D')
        # 读取EV工作表
        ev_ws = workbook['EV']
        
        print(f"pl5数据行数: {len(pl5_df)}")
        print(f"3D数据行数: {len(d3_df)}")
        print(f"EV工作表行数: {ev_ws.max_row}")
        
        # 构建EV工作表的日期映射（日期 -> 行号）
        date_to_row = {}
        for row in range(2, ev_ws.max_row + 1):
            date_cell = ev_ws.cell(row, 1).value  # A列是日期
            if date_cell is None:
                continue
            
            # 处理日期格式 - 统一转换为字符串格式进行比较
            if isinstance(date_cell, datetime):
                date_str = date_cell.strftime('%Y-%m-%d')
            else:
                # 尝试解析字符串日期
                date_str = str(date_cell).strip()
                # 移除时间部分
                if ' ' in date_str:
                    date_str = date_str.split(' ')[0]
            
            date_to_row[date_str] = row
        
        print(f"EV工作表日期映射数量: {len(date_to_row)}")
        
        # 更新pl5数据到EV工作表的B列
        pl5_updated = 0
        for _, row in pl5_df.iterrows():
            date_str = str(row['开奖日期']).strip()
            
            if date_str in date_to_row:
                ev_row = date_to_row[date_str]
                
                # 获取B列的列号
                b_col = 2  # B列
                
                # 检查B列是否已有数据，如果没有则写入
                cell_value = ev_ws.cell(ev_row, b_col).value
                if cell_value is None or cell_value == '':
                    # 获取开奖号码（保留原始格式，带空格）
                    numbers = str(row['开奖号码']).strip()
                    
                    # 确保号码格式正确（5位数字，带空格分隔）
                    clean_numbers = numbers.replace(' ', '')
                    if len(clean_numbers) == 5:
                        # 如果没有空格，添加空格分隔
                        if ' ' not in numbers:
                            numbers = ' '.join(clean_numbers)
                        
                        # 将带空格的5位数字写入B列
                        ev_ws.cell(ev_row, b_col).value = numbers
                        pl5_updated += 1
                        print(f"更新PL5数据: 日期 {date_str}, 号码 {numbers}")
        
        # 更新3D数据到EV工作表的E列
        d3_updated = 0
        for _, row in d3_df.iterrows():
            date_str = str(row['开奖日期']).strip()
            
            if date_str in date_to_row:
                ev_row = date_to_row[date_str]
                
                # 获取E列的列号
                e_col = 5  # E列
                
                # 检查E列是否已有数据，如果没有则写入
                cell_value = ev_ws.cell(ev_row, e_col).value
                if cell_value is None or cell_value == '':
                    # 获取开奖号码（保留原始格式，带空格）
                    numbers = str(row['开奖号码']).strip()
                    
                    # 确保号码格式正确（3位数字，带空格分隔）
                    clean_numbers = numbers.replace(' ', '')
                    if len(clean_numbers) == 3:
                        # 如果没有空格，添加空格分隔
                        if ' ' not in numbers:
                            numbers = ' '.join(clean_numbers)
                        
                        # 将带空格的3位数字写入E列
                        ev_ws.cell(ev_row, e_col).value = numbers
                        d3_updated += 1
                        print(f"更新3D数据: 日期 {date_str}, 号码 {numbers}")
        
        # 保存工作簿
        workbook.save(filename)
        workbook.close()
        
        print(f"PL5更新了 {pl5_updated} 条数据")
        print(f"3D更新了 {d3_updated} 条数据")
        
        return True
        
    except Exception as e:
        print(f"更新EV工作表时出错: {str(e)}")
        if 'workbook' in locals():
            workbook.close()
        return False

# 更新函数
def update_dlt_data(crawler):
    """
    更新大乐透数据：只获取并添加新期数
    """
    existing_df = get_existing_data('Tools.xlsx', 'dltall')
    
    if existing_df.empty:
        with tqdm(total=1, desc="获取大乐透历史数据") as pbar:
            all_data = crawler.get_all_dlt_history()
            pbar.update(1)
            
        if all_data is not None and len(all_data) > 0:
            safe_save_to_excel(all_data, 'Tools.xlsx', 'dltall')
        return
    
    latest_period = existing_df['期号'].max()
    
    latest_data = crawler.get_latest_dlt_data()
    
    if latest_data is None or latest_data.empty:
        return
    
    new_data = latest_data[~latest_data['期号'].isin(existing_df['期号'])]
    
    if new_data.empty:
        return
    
    # 修复日期格式问题
    if '开奖日期' in existing_df.columns:
        existing_df['开奖日期'] = pd.to_datetime(existing_df['开奖日期'], errors='coerce').dt.strftime('%Y-%m-%d')
    
    combined_data = pd.concat([existing_df, new_data], ignore_index=True)
    
    combined_data['开奖日期'] = pd.to_datetime(combined_data['开奖日期'], errors='coerce')
    combined_data = combined_data.dropna(subset=['开奖日期'])
    combined_data = combined_data.sort_values(by='开奖日期', ascending=True)
    combined_data = combined_data.reset_index(drop=True)
    
    combined_data['开奖日期'] = combined_data['开奖日期'].dt.strftime('%Y-%m-%d')
    
    safe_save_to_excel(combined_data, 'Tools.xlsx', 'dltall')

def update_ssq_data(crawler):
    """
    更新双色球数据：只获取并添加新期数
    """
    existing_df = get_existing_data('Tools.xlsx', 'ssq')
    
    if existing_df.empty:
        with tqdm(total=1, desc="获取双色球历史数据") as pbar:
            all_data = crawler.get_all_ssq_history()
            pbar.update(1)
            
        if all_data is not None and len(all_data) > 0:
            safe_save_to_excel(all_data, 'Tools.xlsx', 'ssq')
        return
    
    latest_period = existing_df['期号'].max()
    
    latest_data = crawler.get_latest_ssq_data()
    
    if latest_data is None or latest_data.empty:
        return
    
    new_data = latest_data[~latest_data['期号'].isin(existing_df['期号'])]
    
    if new_data.empty:
        return
    
    # 修复日期格式问题
    # 首先确保现有数据的日期格式一致
    if '开奖日期' in existing_df.columns:
        # 将现有数据的日期转换为统一格式
        existing_df['开奖日期'] = pd.to_datetime(existing_df['开奖日期'], errors='coerce').dt.strftime('%Y-%m-%d')
    
    # 合并数据
    combined_data = pd.concat([existing_df, new_data], ignore_index=True)
    
    # 统一处理日期格式
    combined_data['开奖日期'] = pd.to_datetime(combined_data['开奖日期'], errors='coerce')
    combined_data = combined_data.dropna(subset=['开奖日期'])  # 删除无效日期
    combined_data = combined_data.sort_values(by='开奖日期', ascending=True)
    combined_data = combined_data.reset_index(drop=True)
    
    # 统一格式化为字符串
    combined_data['开奖日期'] = combined_data['开奖日期'].dt.strftime('%Y-%m-%d')
    
    safe_save_to_excel(combined_data, 'Tools.xlsx', 'ssq')

def update_pl5_data(crawler):
    """
    更新排列五数据
    """
    print("\n" + "="*50)
    print("开始更新排列五数据...")
    
    pl5_df = crawler.get_pl5_recent_data(30)
    
    if pl5_df is not None and len(pl5_df) > 0:
        print(f"成功获取 {len(pl5_df)} 条排列五数据")
        # 格式化数据
        pl5_formatted = format_pl5_dataframe(pl5_df)
        
        # 增量保存到Excel文件
        success = incremental_save_to_excel(pl5_formatted, 'Tools.xlsx', 'pl5')
        if success:
            print("排列五数据保存成功!")
        else:
            print("排列五数据保存失败!")
    else:
        print("未获取到排列五数据")

def update_3d_data(crawler):
    """
    更新福彩3D数据
    """
    print("\n" + "="*50)
    print("开始更新福彩3D数据...")
    
    d3_df = crawler.get_3d_recent_data(30)
    
    if d3_df is not None and len(d3_df) > 0:
        print(f"成功获取 {len(d3_df)} 条福彩3D数据")
        # 格式化数据
        d3_formatted = format_3d_dataframe(d3_df)
        
        # 增量保存到Excel文件
        success = incremental_save_to_excel(d3_formatted, 'Tools.xlsx', '3D')
        if success:
            print("福彩3D数据保存成功!")
        else:
            print("福彩3D数据保存失败!")
    else:
        print("未获取到福彩3D数据")

def main():
    """
    主函数 - 更新所有彩票数据
    """
    print("彩票开奖数据获取工具 - 增强版")
    print("=" * 50)
    
    # 创建爬虫实例
    crawler = LotteryDataCrawler()
    
    try:
        # 更新大乐透数据
        print("\n正在更新大乐透数据...")
        update_dlt_data(crawler)
        
        # 更新双色球数据
        print("\n正在更新双色球数据...")
        update_ssq_data(crawler)
        
        # 更新排列五数据
        update_pl5_data(crawler)
        
        # 更新福彩3D数据
        update_3d_data(crawler)
        
        # 将pl5和3D数据更新到EV工作表
        print("\n" + "="*50)
        print("正在将PL5和3D数据更新到EV工作表...")
        success = update_ev_sheet_with_lottery_data('Tools.xlsx')
        
        if success:
            print("EV工作表更新成功!")
        else:
            print("EV工作表更新失败!")
        
    except Exception as e:
        print(f"运行过程中出现错误: {str(e)}")
    
    # 显示保存路径
    file_path = os.path.abspath('Tools.xlsx')
    print(f"\n文件保存路径: {file_path}")
    
    print("\n所有数据更新完成!")

if __name__ == "__main__":
    main()