# -*- coding: utf-8 -*-
"""
五彩种自动分析脚本 (双色球 + 大乐透 + 排列五 + 福彩3D + 七星彩)
运行后生成 HTML 网页报告

- 双色球 / 大乐透: 500.com HTML 表格(含奖池 + 一等奖)
- 排列五 / 福彩3D / 七星彩: 500.com 镜像 XML
- 抓取成功自动写入本地缓存 lottery_cache/*.json
- 数据源失败自动降级：实时 → 本地缓存 → 内置静态数据
- 每彩种面板顶部有"最新开奖大字卡" + 奖池
- 双色球/大乐透近期开奖附一等奖(注数×奖金)
- 大乐透追加一等奖金 = 基本一等奖金 × 80%(官方规则)
- 表格仅显示最新 5 期，分析仍用全部抓取期数(默认15)
- 不自动打开浏览器，适合服务器定时任务

用法:
    python lottery_analysis.py            # 五彩种 各15期
    python lottery_analysis.py all 30     # 五彩种 各30期
    python lottery_analysis.py ssq        # 只跑双色球
    python lottery_analysis.py dlt 20     # 只跑大乐透 20期
    python lottery_analysis.py plw        # 只跑排列五
    python lottery_analysis.py sd         # 只跑福彩3D
    python lottery_analysis.py qxc        # 只跑七星彩
"""
from __future__ import annotations

import json
import random
import re
import sys
from collections import Counter
from datetime import datetime
from pathlib import Path

try:
    import requests
except ImportError:
    requests = None

try:
    from bs4 import BeautifulSoup
except ImportError:
    BeautifulSoup = None

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                  "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
}

TABLE_SHOW = 5

# ===== 一等奖参考默认值(抓不到真实数据时使用) =====
DEFAULT_PRIZE_SSQ = 5000000
DEFAULT_PRIZE_DLT_BASIC = 5000000
# 大乐透追加奖金 = 基本奖金 × 80%
DLT_ADD_RATIO = 0.8

# 数字型彩种每位颜色(按位从左到右)
DIGIT_COLORS = {
    "sd":  ["#e74c3c", "#e67e22", "#27ae60"],
    "plw": ["#e74c3c", "#e67e22", "#27ae60", "#2980b9", "#8e44ad"],
    "qxc": ["#e74c3c", "#e67e22", "#f39c12", "#27ae60", "#16a085", "#2980b9", "#8e44ad"],
}

# 组合策略说明
STRATEGY_HINTS = {
    "ssq": {
        "热号型": "近期出现频次最高的红球为主",
        "邻号型": "以上期号码 ±1 为核心",
        "均衡型": "冷号解冻 + 少量热号补位",
    },
    "dlt": {
        "热号型": "近期出现频次最高的前区号",
        "邻号型": "以上期号码 ±1 为核心",
        "均衡型": "冷号解冻 + 少量热号补位",
    },
    "plw": {
        "热号型": "每位取该位出现最多的数字",
        "次热型": "每位取该位出现次多的数字",
        "冷号型": "每位取该位出现最少的数字",
    },
    "sd": {
        "热号型": "每位取该位出现最多的数字",
        "次热型": "每位取该位出现次多的数字",
        "冷号型": "每位取该位出现最少的数字",
    },
    "qxc": {
        "热号型": "每位取该位出现最多的数字",
        "次热型": "每位取该位出现次多的数字",
        "冷号型": "每位取该位出现最少的数字",
    },
}

CONFIG = {
    "ssq": {
        "name": "双色球", "code": "ssq", "source": "500ssq_html",
        "front_range": (1, 33), "front_pick": 6,
        "back_range": (1, 16),  "back_pick": 1,
        "zones": [(1, 11), (12, 22), (23, 33)],
        "sum_center": (100, 110),
        "static": [
            ("2026104", "2026-09-08", [11, 12, 13, 19, 20, 31], [3]),
            ("2026103", "2026-09-06", [4, 11, 20, 27, 28, 30], [15]),
            ("2026102", "2026-09-03", [3, 4, 10, 13, 16, 25], [9]),
            ("2026101", "2026-09-01", [5, 6, 8, 9, 24, 25], [12]),
            ("2026100", "2026-08-30", [3, 4, 9, 13, 22, 31], [4]),
            ("2026099", "2026-08-27", [1, 12, 14, 18, 30, 31], [2]),
            ("2026098", "2026-08-25", [8, 16, 18, 22, 25, 26], [7]),
            ("2026097", "2026-08-23", [5, 16, 24, 26, 29, 30], [2]),
            ("2026096", "2026-08-20", [1, 4, 16, 22, 26, 31], [4]),
            ("2026095", "2026-08-18", [4, 6, 14, 21, 22, 33], [16]),
            ("2026094", "2026-08-16", [6, 13, 15, 17, 24, 25], [1]),
            ("2026093", "2026-08-13", [5, 8, 15, 20, 21, 24], [9]),
            ("2026092", "2026-08-11", [7, 11, 19, 23, 26, 32], [6]),
            ("2026091", "2026-08-09", [2, 9, 14, 20, 28, 33], [11]),
            ("2026090", "2026-08-06", [1, 6, 10, 17, 25, 31], [8]),
        ],
    },
    "dlt": {
        "name": "大乐透", "code": "dlt", "source": "500html",
        "front_range": (1, 35), "front_pick": 5,
        "back_range": (1, 12),  "back_pick": 2,
        "zones": [(1, 12), (13, 24), (25, 35)],
        "sum_center": (80, 110),
        "static": [
            ("26102", "2026-09-07", [2, 7, 15, 22, 32], [6, 9]),
            ("26101", "2026-09-05", [9, 12, 18, 24, 31], [3, 8]),
            ("26100", "2026-09-03", [5, 8, 16, 22, 33], [2, 10]),
            ("26099", "2026-09-01", [3, 9, 14, 25, 28], [4, 11]),
            ("26098", "2026-08-30", [7, 11, 17, 23, 30], [1, 6]),
            ("26097", "2026-08-27", [4, 10, 19, 26, 34], [5, 12]),
            ("26096", "2026-08-25", [6, 13, 20, 24, 29], [3, 7]),
            ("26095", "2026-08-23", [1, 8, 15, 21, 35], [2, 9]),
            ("26094", "2026-08-20", [11, 14, 22, 27, 32], [4, 10]),
            ("26093", "2026-08-18", [5, 12, 18, 25, 30], [6, 11]),
            ("26092", "2026-08-16", [3, 7, 16, 23, 28], [1, 12]),
            ("26091", "2026-08-13", [8, 15, 21, 26, 35], [2, 9]),
            ("26090", "2026-08-11", [4, 13, 17, 24, 33], [5, 8]),
            ("26089", "2026-08-09", [2, 10, 15, 22, 29], [3, 11]),
            ("26088", "2026-08-06", [6, 9, 19, 27, 31], [1, 7]),
        ],
    },
    "plw": {
        "name": "排列五", "code": "plw", "source": "500plw",
        "digits": 5,
        "digit_range": (0, 9),
        "split_at": None,
        "static": [
            ("26102", "2026-09-08", [1, 3, 5, 7, 9]),
            ("26101", "2026-09-07", [2, 4, 6, 8, 0]),
            ("26100", "2026-09-06", [3, 1, 4, 1, 5]),
            ("26099", "2026-09-05", [9, 8, 7, 6, 5]),
            ("26098", "2026-09-04", [0, 1, 2, 3, 4]),
            ("26097", "2026-09-03", [5, 5, 5, 5, 5]),
            ("26096", "2026-09-02", [1, 2, 3, 4, 5]),
            ("26095", "2026-09-01", [6, 7, 8, 9, 0]),
            ("26094", "2026-08-31", [4, 5, 6, 7, 8]),
            ("26093", "2026-08-30", [9, 0, 1, 2, 3]),
            ("26092", "2026-08-29", [2, 2, 3, 3, 4]),
            ("26091", "2026-08-28", [7, 7, 8, 8, 9]),
            ("26090", "2026-08-27", [1, 1, 2, 2, 3]),
            ("26089", "2026-08-26", [5, 6, 7, 8, 9]),
            ("26088", "2026-08-25", [0, 0, 1, 1, 2]),
        ],
    },
    "sd": {
        "name": "福彩3D", "code": "sd", "source": "500sd",
        "digits": 3,
        "digit_range": (0, 9),
        "split_at": None,
        "static": [
            ("26102", "2026-09-08", [1, 3, 5]),
            ("26101", "2026-09-07", [2, 4, 6]),
            ("26100", "2026-09-06", [3, 1, 4]),
            ("26099", "2026-09-05", [9, 8, 7]),
            ("26098", "2026-09-04", [0, 1, 2]),
            ("26097", "2026-09-03", [5, 5, 5]),
            ("26096", "2026-09-02", [1, 2, 3]),
            ("26095", "2026-09-01", [6, 7, 8]),
            ("26094", "2026-08-31", [4, 5, 6]),
            ("26093", "2026-08-30", [9, 0, 1]),
            ("26092", "2026-08-29", [2, 2, 3]),
            ("26091", "2026-08-28", [7, 7, 8]),
            ("26090", "2026-08-27", [1, 1, 2]),
            ("26089", "2026-08-26", [5, 6, 7]),
            ("26088", "2026-08-25", [0, 0, 1]),
        ],
    },
    "qxc": {
        "name": "七星彩", "code": "qxc", "source": "500qxc",
        "digits": 7,
        "digit_range": (0, 9),
        "split_at": 6,
        "static": [
            ("26102", "2026-09-08", [1, 3, 5, 7, 9, 2, 4]),
            ("26101", "2026-09-07", [2, 4, 6, 8, 0, 1, 3]),
            ("26100", "2026-09-06", [3, 1, 4, 1, 5, 9, 2]),
            ("26099", "2026-09-05", [9, 8, 7, 6, 5, 4, 3]),
            ("26098", "2026-09-04", [0, 1, 2, 3, 4, 5, 6]),
            ("26097", "2026-09-03", [5, 5, 5, 5, 5, 5, 5]),
            ("26096", "2026-09-02", [1, 2, 3, 4, 5, 6, 7]),
            ("26095", "2026-09-01", [6, 7, 8, 9, 0, 1, 2]),
            ("26094", "2026-08-31", [4, 5, 6, 7, 8, 9, 0]),
            ("26093", "2026-08-30", [9, 0, 1, 2, 3, 4, 5]),
            ("26092", "2026-08-29", [2, 2, 3, 3, 4, 4, 5]),
            ("26091", "2026-08-28", [7, 7, 8, 8, 9, 9, 0]),
            ("26090", "2026-08-27", [1, 1, 2, 2, 3, 3, 4]),
            ("26089", "2026-08-26", [5, 6, 7, 8, 9, 0, 1]),
            ("26088", "2026-08-25", [0, 0, 1, 1, 2, 2, 3]),
        ],
    },
}

DIGIT_KINDS = {"sd", "plw", "qxc"}

CACHE_DIR = Path(__file__).resolve().parent / "lottery_cache"


def _cache_path(code: str) -> Path:
    return CACHE_DIR / f"{code}.json"


def _save_cache(code: str, draws: list, extras: dict) -> None:
    try:
        CACHE_DIR.mkdir(exist_ok=True)
        items = []
        for d in draws:
            if len(d) == 4:
                n, dt, f, b = d
                e = (extras or {}).get(str(n), {}) or {}
                items.append({
                    "issue": n, "date": dt,
                    "front": list(f), "back": list(b),
                    "extra": e,
                })
            elif len(d) == 3:
                n, dt, nums = d
                e = (extras or {}).get(str(n), {}) or {}
                items.append({
                    "issue": n, "date": dt,
                    "nums": list(nums), "extra": e,
                })
        payload = {
            "updated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "draws": items,
        }
        _cache_path(code).write_text(
            json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8"
        )
    except Exception as e:
        print(f"  [warn] 写入缓存失败({code}): {e}", flush=True)


def _load_cache(code: str, issue_count: int):
    """返回 (draws, extras, updated_at)；失败返回 None"""
    p = _cache_path(code)
    if not p.exists():
        return None
    try:
        payload = json.loads(p.read_text(encoding="utf-8"))
        draws = []
        extras = {}
        for x in payload.get("draws", []):
            issue = str(x.get("issue"))
            date = str(x.get("date"))
            e = x.get("extra") or {}
            extras[issue] = e
            if "nums" in x:
                draws.append((issue, date, [int(v) for v in x["nums"]]))
            else:
                draws.append((issue, date,
                              [int(v) for v in x["front"]],
                              [int(v) for v in x["back"]]))
        if not draws:
            return None
        return draws[-issue_count:], extras, payload.get("updated_at", "")
    except Exception as e:
        print(f"  [warn] 读取缓存失败({code}): {e}", flush=True)
        return None


# ==================== 数据抓取 ====================

def _safe_int(v):
    """解析带逗号的数字字符串，如 '10,000,000' -> 10000000"""
    if v is None or v == "":
        return None
    try:
        return int(float(str(v).replace(",", "").strip()))
    except (ValueError, TypeError):
        return None


def _extract_prize_from_cells(cells, pool_idx, cnt_idx, amt_idx):
    """从指定列位置尝试提取 (奖池, 注数, 奖金)，并做合理性校验"""
    if pool_idx >= len(cells) or cnt_idx >= len(cells) or amt_idx >= len(cells):
        return None, None, None
    pool = _safe_int(cells[pool_idx])
    cnt = _safe_int(cells[cnt_idx]) or 0
    amt = _safe_int(cells[amt_idx]) or 0
    # 合理性：注数应 < 1000，奖金至少 10 万元
    if 0 < cnt < 1000 and amt > 100000:
        if pool is not None and pool <= 0:
            pool = None
        return pool, cnt, amt
    return None, None, None


def fetch_ssq_html(issue_count: int):
    """
    双色球：500.com HTML 表格(含奖池 + 一等奖)。
    URL: https://datachart.500.com/ssq/history/newinc/history.php

    列布局有两种：
      含"快乐星期天"列(16 列)：
        0=期号 | 1-6=红球 | 7=蓝球 | 8=快乐星期天 | 9=奖池 | 10=一等奖注数 |
        11=一等奖金 | 12=二等奖注数 | 13=二等奖金 | 14=总投注额 | 15=开奖日期
      不含"快乐星期天"列(15 列)：
        0=期号 | 1-6=红球 | 7=蓝球 | 8=奖池 | 9=一等奖注数 |
        10=一等奖金 | 11=二等奖注数 | 12=二等奖金 | 13=总投注额 | 14=开奖日期

    代码会同时尝试两种布局，用"一等奖注数 < 1000"的合理性校验自动选择。
    """
    if requests is None:
        raise RuntimeError("未安装 requests")
    if BeautifulSoup is None:
        raise RuntimeError("未安装 beautifulsoup4 (pip install beautifulsoup4)")

    url = f"https://datachart.500.com/ssq/history/newinc/history.php?limit={issue_count}&sort=0"
    h = dict(HEADERS)
    h["Referer"] = "https://datachart.500.com/ssq/history/history.shtml"
    r = requests.get(url, headers=h, timeout=20)
    r.raise_for_status()
    r.encoding = "gb2312"

    soup = BeautifulSoup(r.text, "html.parser")
    tbody = soup.find("tbody", id="tdata") or soup

    draws, extras = [], {}
    for tr in tbody.find_all("tr"):
        tds = tr.find_all("td")
        if len(tds) < 15:
            continue
        cells = [td.get_text(strip=True) for td in tds]
        issue = cells[0]
        if not issue or not issue.isdigit():
            continue

        # 红球 1-6，蓝球 7
        try:
            front = [int(cells[i]) for i in range(1, 7)]
            back = [int(cells[7])]
        except (ValueError, IndexError):
            continue

        # 尝试两种列布局
        pool, cnt, amt = _extract_prize_from_cells(cells, 9, 10, 11)  # 含快乐星期天
        if cnt is None:
            pool, cnt, amt = _extract_prize_from_cells(cells, 8, 9, 10)  # 不含
        if cnt is None:
            pool, cnt, amt = None, 0, 0

        prize = None
        if cnt > 0 and amt > 0:
            prize = {"count": cnt, "amount": amt}

        extras[issue] = {"pool": pool, "prize": prize}

        # 日期：找最后一个符合日期格式的单元格
        date = ""
        for c in reversed(cells):
            if re.match(r'^\d{4}-\d{2}-\d{2}$', c) or re.match(r'^\d{8}$', c):
                date = c
                break
        if not date and cells:
            date = cells[-1]

        draws.append((issue, date, front, back))
        if len(draws) >= issue_count:
            break

    if not draws:
        raise ValueError("500.com SSQ HTML 未解析到数据")
    draws.reverse()
    return draws, extras, "500.com 镜像(实时)"


def fetch_dlt_html(issue_count: int):
    """
    大乐透：500.com HTML 表格(含奖池 + 一等奖基本)。
    URL: https://datachart.500.com/dlt/history/newinc/history.php

    列布局：
      0=期号 | 1-5=前区 | 6-7=后区 | 8=奖池 | 9=一等奖注数 | 10=一等奖金 |
      11=二等奖注数 | 12=二等奖金 | 13=总投注额 | 14=开奖日期

    追加一等奖金 = 基本一等奖金 × 80% (大乐透官方规则)
    """
    if requests is None:
        raise RuntimeError("未安装 requests")
    if BeautifulSoup is None:
        raise RuntimeError("未安装 beautifulsoup4")

    url = f"https://datachart.500.com/dlt/history/newinc/history.php?limit={issue_count}&sort=0"
    h = dict(HEADERS)
    h["Referer"] = "https://datachart.500.com/dlt/history/history.shtml"
    r = requests.get(url, headers=h, timeout=20)
    r.raise_for_status()
    r.encoding = "gb2312"

    soup = BeautifulSoup(r.text, "html.parser")
    tbody = soup.find("tbody", id="tdata") or soup

    draws, extras = [], {}
    for tr in tbody.find_all("tr"):
        tds = tr.find_all("td")
        if len(tds) < 15:
            continue
        cells = [td.get_text(strip=True) for td in tds]
        issue = cells[0]
        if not issue or not issue.isdigit():
            continue

        # 前区 1-5，后区 6-7
        try:
            front = [int(cells[i]) for i in range(1, 6)]
            back = [int(cells[i]) for i in range(6, 8)]
        except (ValueError, IndexError):
            continue

        # 奖池 8，一等奖注数 9，一等奖金 10
        pool, cnt, amt = _extract_prize_from_cells(cells, 8, 9, 10)
        if cnt is None:
            pool, cnt, amt = None, 0, 0

        basic = None
        add = None
        if cnt > 0 and amt > 0:
            basic = {"count": cnt, "amount": amt}
            # 追加金额 = 基本金额 × 80%
            add = {"amount": int(amt * DLT_ADD_RATIO)}

        prize = None
        if basic:
            prize = {"basic": basic, "additional": add}

        extras[issue] = {"pool": pool, "prize": prize}

        # 日期：找最后一个符合日期格式的单元格
        date = ""
        for c in reversed(cells):
            if re.match(r'^\d{4}-\d{2}-\d{2}$', c) or re.match(r'^\d{8}$', c):
                date = c
                break
        if not date and cells:
            date = cells[-1]

        draws.append((issue, date, front, back))
        if len(draws) >= issue_count:
            break

    if not draws:
        raise ValueError("500.com DLT HTML 未解析到数据")
    draws.reverse()
    return draws, extras, "500.com 镜像(实时)"


def _parse_digit_xml(text: str, issue_count: int, digits: int) -> list:
    from xml.etree import ElementTree as ET
    root = ET.fromstring(text)
    draws = []
    for row in root.findall("row"):
        opencode = (row.get("opencode") or "").strip()
        if not opencode:
            continue
        parts = opencode.replace(",", " ").split()
        if len(parts) != digits:
            continue
        try:
            nums = [int(x) for x in parts]
        except ValueError:
            continue
        if not all(0 <= x <= 9 for x in nums):
            continue
        draws.append((row.get("expect", ""),
                      (row.get("opentime") or "")[:10],
                      nums))
        if len(draws) >= issue_count:
            break

    if not draws:
        raise ValueError("500.com XML 未解析到数字型数据")
    return draws


def fetch_digit(kind: str, issue_count: int):
    """数字型彩种：500.com XML(无奖池数据)"""
    if requests is None:
        raise RuntimeError("未安装 requests")
    cfg = CONFIG[kind]
    url = f"https://datachart.500.com/static/info/kaijiang/xml/{kind}/list.xml"
    h = dict(HEADERS)
    h["Referer"] = f"https://datachart.500.com/{kind}/history/"
    h["Accept"] = "*/*"
    r = requests.get(url, headers=h, timeout=15)
    r.raise_for_status()
    draws = _parse_digit_xml(r.text, issue_count, cfg["digits"])
    draws.reverse()
    extras = {str(n): {"pool": None} for n, _, _ in draws}
    return draws, extras, "500.com 镜像(实时)"


def fetch(kind: str, issue_count: int) -> list:
    cfg = CONFIG[kind]
    code = cfg["code"]
    cfg["_extras"] = {}

    try:
        if requests is None:
            raise RuntimeError("未安装 requests")
        if cfg["source"] == "500ssq_html":
            draws, extras, source = fetch_ssq_html(issue_count)
        elif cfg["source"] == "500html":
            draws, extras, source = fetch_dlt_html(issue_count)
        elif cfg["source"] in ("500plw", "500sd", "500qxc"):
            draws, extras, source = fetch_digit(kind, issue_count)
        else:
            raise RuntimeError(f"未知数据源: {cfg['source']}")
        if not draws:
            raise ValueError("返回为空")

        cfg["_extras"] = extras or {}
        _save_cache(code, draws, cfg["_extras"])
        cfg["_source"] = source
        cfg["_source_cls"] = "source-live"
        return draws
    except Exception as e:
        print(f"  [warn] 实时接口失败({cfg['name']}: {e})，尝试读取本地缓存...", flush=True)

    cached_result = _load_cache(code, issue_count)
    if cached_result:
        draws, cached_extras, updated_at = cached_result
        cfg["_extras"] = cached_extras or {}
        tail = f" {updated_at}" if updated_at else ""
        cfg["_source"] = f"本地缓存(上次实时:{tail})" if tail else "本地缓存"
        cfg["_source_cls"] = "source-cache"
        return draws

    cfg["_source"] = "内置静态数据(非实时)"
    cfg["_source_cls"] = "source-static"
    cfg["_extras"] = {}
    print(f"  [warn] {cfg['name']} 缓存不可用，使用内置静态数据兜底", flush=True)
    return list(cfg["static"][:issue_count])


# ==================== 分析 ====================

def _zone_of(x: int, zones: list) -> int:
    for i, (a, b) in enumerate(zones):
        if a <= x <= b:
            return i
    return 0


def _pick_combo(rng: random.Random, priority: list, num_range: tuple,
                need: int, sum_range: tuple, zones: list,
                max_tries: int = 500) -> list:
    lo, hi = num_range
    prio = [x for x in dict.fromkeys(priority) if lo <= x <= hi]
    prio_set = set(prio)
    others = [x for x in range(lo, hi + 1) if x not in prio_set]

    def valid(cand: list) -> bool:
        if len(cand) != need:
            return False
        if not (sum_range[0] <= sum(cand) <= sum_range[1]):
            return False
        zc = [0] * len(zones)
        for x in cand:
            zc[_zone_of(x, zones)] += 1
        return all(v > 0 for v in zc)

    for keep_n in range(min(len(prio), need), -1, -1):
        keep = prio[:keep_n]
        n_extra = need - keep_n
        if n_extra == 0:
            if valid(sorted(keep)):
                return sorted(keep)
            continue
        for _ in range(max_tries):
            rng.shuffle(others)
            cand = sorted(keep + others[:n_extra])
            if valid(cand):
                return cand

    pool = prio + others
    for _ in range(max_tries * 2):
        rng.shuffle(pool)
        cand = sorted(pool[:need])
        if valid(cand):
            return cand
    return sorted(pool[:need])


def _build_combos(cfg: dict, back_counter: Counter,
                  last_front: list, hot: list, cold: list) -> list:
    num_range = cfg["front_range"]
    need = cfg["front_pick"]
    sum_center = cfg["sum_center"]
    zones = cfg["zones"]

    rng = random.Random(f"{cfg['code']}-{num_range}-{tuple(last_front)}")

    neighbors = sorted({
        x + d for x in last_front for d in (-1, 1)
        if num_range[0] <= x + d <= num_range[1]
    })

    hot_combo = _pick_combo(rng, hot, num_range, need, sum_center, zones)
    neigh_seed = neighbors + [x for x in range(num_range[0], num_range[1] + 1)
                              if x not in set(neighbors)]
    neigh_combo = _pick_combo(rng, neigh_seed, num_range, need, sum_center, zones)
    cold_only = [c for c in cold if c not in set(hot)] or list(cold)
    eq_seed = cold_only[:need] + hot[:2]
    eq_combo = _pick_combo(rng, eq_seed, num_range, need, sum_center, zones)

    bp = cfg["back_pick"]
    br = cfg["back_range"]
    back_sorted = sorted(back_counter, key=lambda x: (-back_counter[x], x))
    if len(back_sorted) < bp * 3:
        back_sorted += [x for x in range(br[0], br[1] + 1) if x not in set(back_sorted)]
    back_sorted = back_sorted[: bp * 3]

    def back_slice(i: int) -> list:
        return sorted(int(x) for x in back_sorted[i * bp:(i + 1) * bp])

    return [
        {"label": "热号型", "front": hot_combo,   "back": back_slice(0)},
        {"label": "邻号型", "front": neigh_combo, "back": back_slice(1)},
        {"label": "均衡型", "front": eq_combo,    "back": back_slice(2)},
    ]


def _analyze_lotto(kind: str, draws: list) -> dict:
    cfg = CONFIG[kind]
    zones = cfg["zones"]
    num_range = cfg["front_range"]
    extras = cfg.get("_extras", {}) or {}

    front_counter = Counter()
    back_counter = Counter()
    for _, _, front, back in draws:
        front_counter.update(front)
        back_counter.update(back)

    n = len(draws)
    hot_threshold = max(2, n // 3)
    cold_threshold = max(1, n // 10)
    hot = sorted(k for k, v in front_counter.items() if v >= hot_threshold)
    cold = [k for k in range(num_range[0], num_range[1] + 1)
            if front_counter.get(k, 0) <= cold_threshold]

    hot_set, cold_set = set(hot), set(cold)

    freq = []
    for num in range(num_range[0], num_range[1] + 1):
        c = front_counter.get(num, 0)
        cls = "hot" if num in hot_set else ("cold" if num in cold_set else "")
        freq.append({"num": num, "count": c, "cls": cls, "zone": _zone_of(num, zones)})

    back_freq = [
        {"num": k, "count": back_counter.get(k, 0)}
        for k in range(cfg["back_range"][0], cfg["back_range"][1] + 1)
    ]

    last_front = draws[-1][2]
    combos = _build_combos(cfg, back_counter, last_front, hot, cold)

    table = []
    for num, date, front, back in draws:
        e = extras.get(str(num), {}) or {}
        table.append({
            "issue": num,
            "date": (date or "").replace("-", ""),
            "front": front,
            "back": back,
            "front_zone": [_zone_of(x, zones) for x in front],
            "pool": e.get("pool"),
            "prize": e.get("prize"),
        })

    latest_pool = table[-1].get("pool") if table else None

    return {
        "kind": kind,
        "name": cfg["name"],
        "source": cfg.get("_source", "未知"),
        "source_cls": cfg.get("_source_cls", "source-static"),
        "count": n,
        "rule": (f"前区 {num_range[0]}-{num_range[1]} 选{cfg['front_pick']}"
                 f" + 后区 {cfg['back_range'][0]}-{cfg['back_range'][1]} 选{cfg['back_pick']}"),
        "zones": zones,
        "sum_center": cfg["sum_center"],
        "table": table,
        "freq": freq,
        "back_freq": back_freq,
        "combos": combos,
        "latest_pool": latest_pool,
    }


def _build_digit_combos(pos_counters: list, d_lo: int, d_hi: int, digits: int) -> list:
    def ranked(counter: Counter) -> list:
        return sorted(range(d_lo, d_hi + 1),
                      key=lambda x: (-counter.get(x, 0), -x))

    hot, second, cold = [], [], []
    for i in range(digits):
        cnt = pos_counters[i] if i < len(pos_counters) else Counter()
        order = ranked(cnt)
        hot.append(order[0] if len(order) >= 1 else d_lo)
        second.append(order[1] if len(order) >= 2 else (order[0] if order else d_lo))
        cold.append(order[-1] if order else d_lo)

    return [
        {"label": "热号型", "nums": hot},
        {"label": "次热型", "nums": second},
        {"label": "冷号型", "nums": cold},
    ]


def _analyze_digit(kind: str, draws: list) -> dict:
    cfg = CONFIG[kind]
    digits = cfg["digits"]
    d_lo, d_hi = cfg["digit_range"]
    extras = cfg.get("_extras", {}) or {}

    pos_counters = [Counter() for _ in range(digits)]
    sums = []
    for _, _, nums in draws:
        sums.append(sum(nums))
        for i, v in enumerate(nums[:digits]):
            pos_counters[i][v] += 1

    pos_freq = []
    for pc in pos_counters:
        pos_freq.append([
            {"num": k, "count": pc.get(k, 0)}
            for k in range(d_lo, d_hi + 1)
        ])

    n = len(draws)
    avg_sum = round(sum(sums) / n, 1) if n else 0
    sum_max = digits * d_hi

    combos = _build_digit_combos(pos_counters, d_lo, d_hi, digits)

    table = []
    for issue, date, nums in draws:
        e = extras.get(str(issue), {}) or {}
        table.append({
            "issue": issue,
            "date": (date or "").replace("-", ""),
            "nums": nums,
            "pool": e.get("pool"),
        })

    latest_pool = table[-1].get("pool") if table else None

    return {
        "kind": kind,
        "name": cfg["name"],
        "source": cfg.get("_source", "未知"),
        "source_cls": cfg.get("_source_cls", "source-static"),
        "count": n,
        "rule": f"每位 {d_lo}-{d_hi}，共 {digits} 位",
        "digits": digits,
        "digit_range": (d_lo, d_hi),
        "split_at": cfg.get("split_at"),
        "table": table,
        "pos_freq": pos_freq,
        "sums": sums,
        "avg_sum": avg_sum,
        "sum_max": sum_max,
        "combos": combos,
        "latest_pool": latest_pool,
    }


def analyze(kind: str, draws: list) -> dict:
    if kind in DIGIT_KINDS:
        return _analyze_digit(kind, draws)
    return _analyze_lotto(kind, draws)


# ==================== HTML 渲染 ====================

HTML_TEMPLATE = r"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>彩票走势分析报告</title>
<style>
:root{
  --ssq:#c0392b; --dlt:#2980b9; --plw:#16a085; --sd:#e67e22; --qxc:#8e44ad;
  --bg:#f2f3f7; --card:#fff;
  --z0:#e74c3c; --z1:#27ae60; --z2:#2980b9; --hot:#e67e22; --cold:#95a5a6;
  --prize:#d35400;
}
*{box-sizing:border-box;margin:0;padding:0}
body{font-family:"Microsoft YaHei","PingFang SC",-apple-system,sans-serif;
  background:var(--bg);color:#2c3e50;padding:16px;line-height:1.6;
  -webkit-text-size-adjust:100%}
.wrap{max-width:960px;margin:0 auto}
h1{text-align:center;font-size:22px;margin-bottom:6px}
.subtitle{text-align:center;color:#7f8c8d;font-size:12px;margin-bottom:12px}
.tabs{display:flex;gap:10px;justify-content:center;margin-bottom:12px;flex-wrap:wrap}
.tab{padding:9px 22px;border-radius:22px;cursor:pointer;font-size:14px;font-weight:bold;
  background:#fff;border:2px solid #ddd;color:#555;transition:.2s;
  user-select:none;-webkit-tap-highlight-color:transparent}
.tab.active{border-color:transparent;color:#fff}
.tab[data-k="ssq"].active{background:var(--ssq)}
.tab[data-k="dlt"].active{background:var(--dlt)}
.tab[data-k="plw"].active{background:var(--plw)}
.tab[data-k="sd"].active{background:var(--sd)}
.tab[data-k="qxc"].active{background:var(--qxc)}
.panel{display:none;animation:fade .3s}
.panel.active{display:block}
@keyframes fade{from{opacity:0;transform:translateY(8px)}to{opacity:1;transform:none}}
.card{background:var(--card);border-radius:12px;padding:16px;margin-bottom:16px;box-shadow:0 1px 8px rgba(0,0,0,.06)}
.card h2{font-size:16px;margin-bottom:12px;padding-left:10px;border-left:4px solid currentColor}
.card h2.ssq{color:var(--ssq);border-color:var(--ssq)}
.card h2.dlt{color:var(--dlt);border-color:var(--dlt)}
.card h2.plw{color:var(--plw);border-color:var(--plw)}
.card h2.sd{color:var(--sd);border-color:var(--sd)}
.card h2.qxc{color:var(--qxc);border-color:var(--qxc)}
.meta{display:flex;gap:12px;flex-wrap:wrap;font-size:12px;color:#555}
.meta b{color:#2c3e50}
.source-live{color:#27ae60;font-weight:bold}
.source-cache{color:#2980b9;font-weight:bold}
.source-static{color:#e67e22;font-weight:bold}
.legend{display:flex;gap:14px;flex-wrap:wrap;font-size:11px;color:#666;margin-bottom:10px}
.legend span{display:inline-flex;align-items:center;gap:4px}
.dot{width:12px;height:12px;border-radius:50%;display:inline-block}
table{width:100%;border-collapse:collapse;font-size:12px}
th,td{padding:6px 4px;text-align:center;border-bottom:1px solid #eee}
th{background:#f8f9fa;color:#555;font-weight:600;white-space:nowrap}
th.num-col, td.num-col{text-align:left;white-space:nowrap;padding-left:8px}
tr.latest td{background:#fff8e1;font-weight:bold}
.ball{display:inline-flex;align-items:center;justify-content:center;min-width:26px;height:26px;
  padding:0 1px;border-radius:50%;color:#fff;font-size:12px;font-weight:bold;margin:0 2px}
.ball.z0,.freq-item.z0{background:var(--z0)}
.ball.z1,.freq-item.z1{background:var(--z1)}
.ball.z2,.freq-item.z2{background:var(--z2)}
.ball.back{background:#8e44ad}
.ball-sep{display:inline-block;color:#b2bec3;font-weight:bold;font-size:14px;
  margin:0 6px;vertical-align:middle;line-height:1}
.latest-card{
  background:linear-gradient(135deg,#fafbfe,#eef2f9);
  border-radius:14px;padding:22px 14px;text-align:center;
  border:1px solid #e8eef6;
}
.latest-meta{font-size:12px;color:#7f8c8d;margin-bottom:10px;letter-spacing:.5px}
.latest-pool{
  display:inline-block;
  font-size:12px;
  color:#d35400;
  background:rgba(230,126,34,.10);
  padding:3px 14px;
  border-radius:14px;
  margin-bottom:14px;
  letter-spacing:.3px;
  font-weight:600;
}
.latest-pool b{
  color:#c0392b;
  font-size:15px;
  margin-left:5px;
  font-weight:800;
}
.latest-numbers{display:flex;justify-content:center;align-items:center;flex-wrap:wrap;gap:2px 0}
.ball.big{
  min-width:46px;height:46px;font-size:18px;font-weight:800;
  margin:0 4px;padding:0 4px;
  box-shadow:0 3px 8px rgba(0,0,0,.15),inset 0 -3px 5px rgba(0,0,0,.12),
             inset 0 3px 5px rgba(255,255,255,.25);
}
.ball-sep.big{font-size:22px;margin:0 10px}
.freq-grid{display:grid;grid-template-columns:repeat(auto-fill,minmax(38px,1fr));gap:6px 3px}
.freq-item{position:relative;display:flex;align-items:center;justify-content:center;
  width:34px;height:34px;border-radius:50%;color:#fff;font-size:12px;font-weight:bold;
  margin:0 auto;border:2px solid transparent;flex:none}
.freq-item .cnt{position:absolute;right:-4px;bottom:-4px;
  min-width:16px;height:16px;padding:0 4px;border-radius:9px;
  background:#1a1a1a;color:#fff;font-size:9px;font-weight:800;
  display:flex;align-items:center;justify-content:center;line-height:1;
  border:1.5px solid #fff;box-shadow:0 1px 3px rgba(0,0,0,.35);z-index:2}
.freq-item.hot{box-shadow:0 0 0 2px var(--hot)}
.freq-item.cold{opacity:.35}
.back-grid{display:flex;gap:6px;flex-wrap:wrap;justify-content:center}
.pos-block{margin-bottom:10px}
.pos-block .pos-label{font-size:12px;color:#666;margin-bottom:4px;font-weight:bold}
.pos-grid{display:grid;grid-template-columns:repeat(10,30px);
  justify-content:center;gap:3px 4px}
.pos-grid .freq-item{width:26px;height:26px;font-size:10.5px;margin:0}
.combos{display:grid;grid-template-columns:repeat(auto-fit,minmax(300px,1fr));gap:14px}
.combo{background:#f8f9fa;border-radius:10px;padding:14px 16px;border-top:3px solid #bbb;overflow:hidden}
.combo.hot{border-top-color:var(--hot)}
.combo.neigh{border-top-color:var(--dlt)}
.combo.eq{border-top-color:var(--z1)}
.combo.dig-a{border-top-color:var(--plw)}
.combo.dig-b{border-top-color:#3498db}
.combo.dig-c{border-top-color:#95a5a6}
.combo .tag{display:flex;justify-content:space-between;align-items:center;gap:8px;
  font-size:12px;color:#7f8c8d;margin-bottom:4px}
.combo .strategy{font-size:11px;color:#95a5a6;margin-bottom:10px;line-height:1.5}
.combo .line{display:flex;align-items:center;flex-wrap:nowrap;white-space:nowrap}
.combo .sep{margin:0 6px;color:#bbb;font-weight:bold}
.copy-btn{padding:2px 10px;border-radius:12px;border:1px solid #cbd5e0;
  background:#fff;color:#555;font-size:11px;font-weight:600;cursor:pointer;
  user-select:none;-webkit-tap-highlight-color:transparent;transition:.15s;
  font-family:inherit;line-height:1.6;white-space:nowrap;flex:none}
.copy-btn:hover{background:#eef2f7;border-color:#a0aec0}
.copy-btn:active{transform:scale(.96)}
.copy-btn.copied{background:#27ae60;border-color:#27ae60;color:#fff}
.note{background:#f8f9fa;border:1px solid #e9ecef;border-radius:8px;
  padding:8px 14px;color:#999;font-size:11px;text-align:center;line-height:1.6}
.note .dot-sep{margin:0 6px;color:#ddd}
.summary{display:flex;gap:16px;flex-wrap:wrap;font-size:12px;color:#555;margin-top:8px}
.summary b{color:#2c3e50}

/* ===== 一等奖单元格(强调色) ===== */
.prize-cell{
  text-align:left !important;
  font-size:13px;
  font-weight:700;
  line-height:1.75;
  color:var(--prize);
  padding-left:10px !important;
  min-width:180px;
  white-space:nowrap;
}
.prize-line{
  display:flex;
  align-items:center;
  gap:5px;
}
.prize-label{
  display:inline-block;
  padding:0 5px;
  background:#fdebd0;
  color:#b9770e;
  border-radius:3px;
  font-size:10px;
  font-weight:bold;
  line-height:16px;
  flex:none;
}
.prize-ref{
  color:#c8cfd6;
  font-style:italic;
  font-weight:500;
}

@media(max-width:600px){
  body{padding:8px;font-size:13px}
  h1{font-size:18px;margin-bottom:4px}
  .subtitle{font-size:11px;line-height:1.5;margin-bottom:8px;padding:0 4px}
  .tabs{gap:6px;margin-bottom:12px}
  .tab{padding:6px 12px;font-size:12px;border-radius:16px;font-weight:600}
  .card{padding:12px;border-radius:10px;margin-bottom:10px}
  .card h2{font-size:14px;margin-bottom:8px;padding-left:8px;border-left-width:3px}
  .meta{font-size:11px;gap:6px 12px}
  .legend{font-size:10.5px;gap:8px;margin-bottom:8px}
  .dot{width:10px;height:10px}
  table{font-size:11px}
  th,td{padding:5px 2px}
  th.num-col, td.num-col{padding-left:4px}
  .ball{min-width:20px;height:20px;font-size:10px;margin:0 1px;padding:0}
  .ball-sep{margin:0 3px;font-size:12px}
  .latest-card{padding:16px 8px;border-radius:12px}
  .latest-meta{font-size:11px;margin-bottom:8px}
  .latest-pool{font-size:11px;padding:2px 10px;margin-bottom:10px;}
  .latest-pool b{font-size:13px;margin-left:3px;}
  .ball.big{min-width:34px;height:34px;font-size:14px;margin:0 2px}
  .ball-sep.big{font-size:16px;margin:0 6px}
  .freq-grid{grid-template-columns:repeat(auto-fill,minmax(28px,1fr));gap:5px 2px}
  .freq-item{width:26px;height:26px;font-size:10px}
  .freq-item .cnt{min-width:13px;height:13px;font-size:8.5px;padding:0 3px;
    right:-2px;bottom:-2px;border-width:1px}
  .pos-block{margin-bottom:8px}
  .pos-block .pos-label{font-size:11px;margin-bottom:3px}
  .pos-grid{grid-template-columns:repeat(10,1fr);gap:3px 2px;justify-content:stretch}
  .pos-grid .freq-item{width:100%;max-width:28px;height:auto;aspect-ratio:1/1;
    font-size:10px;margin:0 auto}
  .combos{grid-template-columns:1fr;gap:8px}
  .combo{padding:10px 12px;border-radius:8px}
  .combo .tag{font-size:11px;margin-bottom:3px}
  .combo .strategy{font-size:10.5px;margin-bottom:8px}
  .combo .sep{margin:0 4px;font-size:13px}
  .copy-btn{padding:3px 9px;font-size:10px}
  .note{padding:6px 10px;font-size:10px;line-height:1.5}
  .summary{font-size:11px;gap:8px;margin-top:6px}
  .prize-cell{
    font-size:11px;
    min-width:140px;
    padding-left:4px !important;
  }
  .prize-label{
    font-size:9px;
    padding:0 3px;
    line-height:14px;
  }
}
</style>
</head>
<body>
<div class="wrap">
<h1>🎯 彩票走势分析</h1>
<div class="subtitle">生成时间：__GENERATED_AT__</div>

<div class="tabs">
  __TABS__
</div>

__PANELS__

<div class="note">
  彩票为独立随机事件，走势不能预测未来<span class="dot-sep">·</span>号码仅基于历史频率推演，仅供娱乐参考，非投注建议<span class="dot-sep">·</span>请理性购彩、量力而行
</div>
</div>

<script>
document.querySelectorAll('.tab').forEach(function(t){
  t.onclick=function(){
    document.querySelectorAll('.tab').forEach(function(x){x.classList.remove('active')});
    document.querySelectorAll('.panel').forEach(function(x){x.classList.remove('active')});
    t.classList.add('active');
    var p=document.getElementById('panel-'+t.dataset.k);
    if(p) p.classList.add('active');
  };
});

function _fallbackCopy(text, done){
  var ta = document.createElement('textarea');
  ta.value = text;
  ta.setAttribute('readonly', '');
  ta.style.position = 'fixed';
  ta.style.top = '0';
  ta.style.left = '-9999px';
  document.body.appendChild(ta);
  ta.select();
  ta.setSelectionRange(0, text.length);
  var ok = false;
  try { ok = document.execCommand('copy'); } catch(e) { ok = false; }
  document.body.removeChild(ta);
  if(ok) done(); else alert('复制失败，请手动选择号码');
}

document.querySelectorAll('.copy-btn').forEach(function(btn){
  btn.addEventListener('click', function(e){
    e.stopPropagation();
    var text = btn.dataset.copy || '';
    if(!text) return;
    var finish = function(){
      var old = btn.textContent;
      btn.textContent = '✓ 已复制';
      btn.classList.add('copied');
      btn.disabled = true;
      setTimeout(function(){
        btn.textContent = old;
        btn.classList.remove('copied');
        btn.disabled = false;
      }, 1500);
    };
    if(navigator.clipboard && window.isSecureContext){
      navigator.clipboard.writeText(text).then(finish).catch(function(){
        _fallbackCopy(text, finish);
      });
    } else {
      _fallbackCopy(text, finish);
    }
  });
});
</script>
</body>
</html>
"""


def _fmt_money(v):
    if v is None:
        return "—"
    try:
        v = int(v)
    except (TypeError, ValueError):
        return "—"
    if v <= 0:
        return "—"
    if v >= 1e8:
        return f"{v/1e8:.2f}亿"
    if v >= 1e4:
        return f"{v/1e4:.1f}万"
    return f"{v}元"


def _render_balls(front: list, front_zone: list, back: list, big: bool = False) -> str:
    cls = "ball big" if big else "ball"
    parts = []
    for i, x in enumerate(front):
        z = front_zone[i] if i < len(front_zone) else 0
        parts.append(f'<span class="{cls} z{z}">{int(x):02d}</span>')
    if back:
        sep_cls = "ball-sep big" if big else "ball-sep"
        parts.append(f'<span class="{sep_cls}">+</span>')
        for x in back:
            back_cls = f'{cls} back'
            parts.append(f'<span class="{back_cls}">{int(x):02d}</span>')
    return "".join(parts)


def _copy_text_lotto(front: list, back: list) -> str:
    s = " ".join(f"{int(x):02d}" for x in front)
    if back:
        s += " + " + " ".join(f"{int(x):02d}" for x in back)
    return s


def _copy_text_digit(nums: list, split_at) -> str:
    parts = [str(int(x)) for x in nums]
    if split_at is not None and 0 < split_at < len(parts):
        return " ".join(parts[:split_at]) + " + " + " ".join(parts[split_at:])
    return " ".join(parts)


def _render_latest_card_lotto(d: dict) -> str:
    if not d["table"]:
        return ""
    last = d["table"][-1]
    kind = d["kind"]
    cls = "ssq" if kind == "ssq" else "dlt"
    balls = _render_balls(last["front"], last["front_zone"], last["back"], big=True)
    pool = d.get("latest_pool")
    pool_str = _fmt_money(pool) if pool else "—"
    pool_html = f'<div class="latest-pool">💰 奖池 <b>{pool_str}</b></div>'
    return f"""
  <div class="card">
    <h2 class="{cls}">最新开奖</h2>
    <div class="latest-card">
      <div class="latest-meta">第 {last['issue']} 期 · {last['date']}</div>
      {pool_html}
      <div class="latest-numbers">{balls}</div>
    </div>
  </div>
"""


def _render_latest_card_digit(d: dict) -> str:
    if not d["table"]:
        return ""
    last = d["table"][-1]
    kind = d["kind"]
    colors = DIGIT_COLORS[kind]
    split_at = d.get("split_at")
    parts = []
    for i, x in enumerate(last["nums"]):
        if split_at is not None and i == split_at:
            parts.append('<span class="ball-sep big">+</span>')
        color = colors[i % len(colors)]
        parts.append(f'<span class="ball big" style="background:{color}">{int(x)}</span>')
    pool = d.get("latest_pool")
    pool_str = _fmt_money(pool) if pool else "—"
    pool_html = f'<div class="latest-pool">💰 奖池 <b>{pool_str}</b></div>'
    return f"""
  <div class="card">
    <h2 class="{kind}">最新开奖</h2>
    <div class="latest-card">
      <div class="latest-meta">第 {last['issue']} 期 · {last['date']}</div>
      {pool_html}
      <div class="latest-numbers">{"".join(parts)}</div>
    </div>
  </div>
"""


def _render_prize_cell(kind: str, prize) -> str:
    """一等奖单元格(仅双色球/大乐透)。
    大乐透追加金额 = 基本奖金 × 80%(官方规则)，只显示金额不显示注数。
    """
    if kind == "ssq":
        cnt = int((prize or {}).get("count") or 0)
        amt = int((prize or {}).get("amount") or 0)
        if cnt > 0 and amt > 0:
            body = f'{cnt}注 × {_fmt_money(amt)}'
        else:
            body = f'<span class="prize-ref">{_fmt_money(DEFAULT_PRIZE_SSQ)}</span>'
        return f'<td class="prize-cell"><div class="prize-line">{body}</div></td>'

    # 大乐透
    basic = (prize or {}).get("basic") or {}
    add = (prize or {}).get("additional") or {}

    b_cnt = int(basic.get("count") or 0)
    b_amt = int(basic.get("amount") or 0)
    a_amt = int(add.get("amount") or 0)

    if b_cnt > 0 and b_amt > 0:
        line_basic = f'{b_cnt}注 × {_fmt_money(b_amt)}'
    else:
        line_basic = f'<span class="prize-ref">{_fmt_money(DEFAULT_PRIZE_DLT_BASIC)}</span>'

    # 追加金额：优先用解析到的值，否则用基本金额 × 80% 算
    if a_amt > 0:
        line_add = _fmt_money(a_amt)
    elif b_amt > 0:
        line_add = _fmt_money(int(b_amt * DLT_ADD_RATIO))
    else:
        line_add = f'<span class="prize-ref">{_fmt_money(int(DEFAULT_PRIZE_DLT_BASIC * DLT_ADD_RATIO))}</span>'

    return (
        '<td class="prize-cell">'
        f'<div class="prize-line"><span class="prize-label">基本</span>{line_basic}</div>'
        f'<div class="prize-line"><span class="prize-label">追加</span>{line_add}</div>'
        '</td>'
    )


def _render_panel_lotto(d: dict) -> str:
    kind = d["kind"]
    cls = "ssq" if kind == "ssq" else "dlt"
    source_cls = d.get("source_cls", "source-static")
    zones = d["zones"]
    hints = STRATEGY_HINTS.get(kind, {})

    latest_card = _render_latest_card_lotto(d)

    recent = d["table"][-TABLE_SHOW:] if d["table"] else []
    last_issue = recent[-1]["issue"] if recent else None
    rows = []
    for row in recent:
        tr_cls = ' class="latest"' if row["issue"] == last_issue else ''
        balls_html = _render_balls(row["front"], row["front_zone"], row["back"])
        prize_td = _render_prize_cell(kind, row.get("prize"))
        rows.append(
            f'<tr{tr_cls}>'
            f'<td>{row["issue"]}</td>'
            f'<td>{row["date"]}</td>'
            f'<td class="num-col">{balls_html}</td>'
            f'{prize_td}'
            f'</tr>'
        )
    table_html = (
        '<table><thead><tr><th>期号</th><th>日期</th>'
        '<th class="num-col">号码</th><th>一等奖</th></tr></thead>'
        '<tbody>' + "".join(rows) + '</tbody></table>'
    )

    items = []
    for item in d["freq"]:
        num, cnt, z = int(item["num"]), int(item["count"]), item["zone"]
        ccls = item["cls"]
        badge = f'<span class="cnt">{cnt}</span>' if cnt > 0 else ""
        items.append(
            f'<div class="freq-item {ccls} z{z}" title="{num:02d} 出现 {cnt} 次">'
            f'{num:02d}{badge}</div>'
        )
    legend = (
        '<div class="legend">'
        f'<span><i class="dot" style="background:var(--z0)"></i>一区 {zones[0][0]:02d}-{zones[0][1]:02d}</span>'
        f'<span><i class="dot" style="background:var(--z1)"></i>二区 {zones[1][0]:02d}-{zones[1][1]:02d}</span>'
        f'<span><i class="dot" style="background:var(--z2)"></i>三区 {zones[2][0]:02d}-{zones[2][1]:02d}</span>'
        '<span><i class="dot" style="border:2px solid var(--hot);background:#fff"></i>热号(高频)</span>'
        '<span><i class="dot" style="background:#bbb;opacity:.4"></i>冷号(低频)</span>'
        '<span style="color:#999">· 球上数字=出现次数</span>'
        '</div>'
    )
    freq_html = legend + '<div class="freq-grid">' + "".join(items) + '</div>'

    max_bc = max((item["count"] for item in d["back_freq"]), default=1) or 1
    back_items = []
    for item in d["back_freq"]:
        num, cnt = int(item["num"]), int(item["count"])
        ratio = cnt / max_bc
        opacity = 0.35 + 0.65 * ratio
        size = 28 + int(12 * ratio)
        back_items.append(
            f'<div class="freq-item" style="width:{size}px;height:{size}px;'
            f'background:rgba(142,68,173,{opacity:.2f});border:2px solid #8e44ad" '
            f'title="后区 {num:02d} 出现 {cnt} 次">{num:02d}'
            f'<span class="cnt">{cnt}</span></div>'
        )
    back_freq_html = '<div class="back-grid">' + "".join(back_items) + '</div>'

    combo_cls = ["hot", "neigh", "eq"]
    combo_cards = []
    for i, c in enumerate(d["combos"]):
        front_zone = [_zone_of(x, zones) for x in c["front"]]
        front_html = "".join(
            f'<span class="ball z{front_zone[j]}">{int(x):02d}</span>'
            for j, x in enumerate(c["front"])
        )
        back_html = "".join(f'<span class="ball back">{int(x):02d}</span>' for x in c["back"])
        copy_text = _copy_text_lotto(c["front"], c["back"])
        hint = hints.get(c["label"], "")
        hint_html = f'<div class="strategy">{hint}</div>' if hint else ""
        combo_cards.append(
            f'<div class="combo {combo_cls[i]}">'
            f'<div class="tag">'
            f'<span>组合{i + 1} · {c["label"]}</span>'
            f'<button type="button" class="copy-btn" data-copy="{copy_text}">📋 复制</button>'
            f'</div>'
            f'{hint_html}'
            f'<div class="line">{front_html}<span class="sep">+</span>{back_html}</div>'
            f'</div>'
        )
    combos_html = '<div class="combos">' + "".join(combo_cards) + '</div>'

    return f"""
<div class="panel {kind}" id="panel-{kind}">
  <div class="card">
    <div class="meta">
      <span><b>{d['name']}</b>（{d['rule']}）</span>
      <span>数据来源：<span class="{source_cls}">{d['source']}</span></span>
      <span>分析期数：{d['count']}</span>
    </div>
  </div>
{latest_card}
  <div class="card">
    <h2 class="{cls}">近期开奖（最新 {TABLE_SHOW} 期，最新一期置底高亮）</h2>
    {table_html}
  </div>

  <div class="card">
    <h2 class="{cls}">号码频率（按区间分色）</h2>
    {freq_html}
  </div>

  <div class="card">
    <h2 class="{cls}">后区频率</h2>
    {back_freq_html}
  </div>

  <div class="card">
    <h2 class="{cls}">下期参考（仅供娱乐）</h2>
    {combos_html}
  </div>
</div>
"""


def _render_panel_digit(d: dict) -> str:
    kind = d["kind"]
    cls = kind
    source_cls = d.get("source_cls", "source-static")
    colors = DIGIT_COLORS[kind]
    digits = d["digits"]
    split_at = d.get("split_at")
    hints = STRATEGY_HINTS.get(kind, {})

    latest_card = _render_latest_card_digit(d)

    recent = d["table"][-TABLE_SHOW:] if d["table"] else []
    last_issue = recent[-1]["issue"] if recent else None
    rows = []
    for row in recent:
        tr_cls = ' class="latest"' if row["issue"] == last_issue else ''
        parts = []
        for i, x in enumerate(row["nums"]):
            if split_at is not None and i == split_at:
                parts.append('<span class="ball-sep">+</span>')
            color = colors[i % len(colors)]
            parts.append(f'<span class="ball" style="background:{color}">{int(x)}</span>')
        rows.append(
            f'<tr{tr_cls}>'
            f'<td>{row["issue"]}</td>'
            f'<td>{row["date"]}</td>'
            f'<td class="num-col">{"".join(parts)}</td>'
            f'</tr>'
        )
    table_html = (
        f'<table><thead><tr><th>期号</th><th>日期</th>'
        f'<th class="num-col">号码（{digits}位）</th></tr></thead>'
        '<tbody>' + "".join(rows) + '</tbody></table>'
    )

    pos_blocks = []
    for i, pf in enumerate(d["pos_freq"]):
        color = colors[i % len(colors)]
        max_c = max((x["count"] for x in pf), default=1) or 1
        items = []
        for item in pf:
            num, cnt = int(item["num"]), int(item["count"])
            ratio = cnt / max_c
            opacity = 0.30 + 0.70 * ratio
            items.append(
                f'<div class="freq-item" '
                f'style="background:{color};opacity:{opacity:.2f};border:2px solid {color}" '
                f'title="第{i+1}位 {num} 出现 {cnt} 次">{num}'
                f'<span class="cnt">{cnt}</span></div>'
            )
        pos_blocks.append(
            f'<div class="pos-block">'
            f'<div class="pos-label" style="color:{color}">第 {i + 1} 位</div>'
            f'<div class="pos-grid">' + "".join(items) + '</div>'
            f'</div>'
        )
    pos_freq_html = "".join(pos_blocks)

    combo_cls = ["dig-a", "dig-b", "dig-c"]
    combo_cards = []
    for i, c in enumerate(d["combos"]):
        parts = []
        for j, x in enumerate(c["nums"]):
            if split_at is not None and j == split_at:
                parts.append('<span class="sep">+</span>')
            color = colors[j % len(colors)]
            parts.append(f'<span class="ball" style="background:{color}">{int(x)}</span>')
        copy_text = _copy_text_digit(c["nums"], split_at)
        hint = hints.get(c["label"], "")
        hint_html = f'<div class="strategy">{hint}</div>' if hint else ""
        combo_cards.append(
            f'<div class="combo {combo_cls[i]}">'
            f'<div class="tag">'
            f'<span>组合{i + 1} · {c["label"]}</span>'
            f'<button type="button" class="copy-btn" data-copy="{copy_text}">📋 复制</button>'
            f'</div>'
            f'{hint_html}'
            f'<div class="line">{"".join(parts)}</div>'
            f'</div>'
        )
    combos_html = '<div class="combos">' + "".join(combo_cards) + '</div>'

    d_lo, d_hi = d["digit_range"]
    sum_max = d["sum_max"]

    return f"""
<div class="panel {kind}" id="panel-{kind}">
  <div class="card">
    <div class="meta">
      <span><b>{d['name']}</b>（{d['rule']}）</span>
      <span>数据来源：<span class="{source_cls}">{d['source']}</span></span>
    </div>
    <div class="summary">
      <span>分析期数：<b>{d['count']}</b></span>
      <span>最近 {d['count']} 期和值均值：<b>{d['avg_sum']}</b>（0-{sum_max} 区间）</span>
    </div>
  </div>
{latest_card}
  <div class="card">
    <h2 class="{cls}">近期开奖（最新 {TABLE_SHOW} 期，最新一期置底高亮）</h2>
    {table_html}
  </div>

  <div class="card">
    <h2 class="{cls}">各位位置频率</h2>
    {pos_freq_html}
  </div>

  <div class="card">
    <h2 class="{cls}">下期参考（仅供娱乐）</h2>
    {combos_html}
  </div>
</div>
"""


def render_panel(d: dict) -> str:
    if d["kind"] in DIGIT_KINDS:
        return _render_panel_digit(d)
    return _render_panel_lotto(d)


def render_html(reports: list) -> str:
    kind_labels = {
        "ssq": "🔴 双色球",
        "dlt": "🔵 大乐透",
        "plw": "🟢 排列五",
        "sd":  "🟠 福彩3D",
        "qxc": "🟣 七星彩",
    }
    first_kind = reports[0]["kind"] if reports else None

    tabs = []
    for d in reports:
        label = kind_labels.get(d["kind"], d["kind"])
        active = "active" if d["kind"] == first_kind else ""
        tabs.append(f'<div class="tab {active}" data-k="{d["kind"]}">{label}</div>')

    panels = []
    for d in reports:
        p = render_panel(d)
        if d["kind"] == first_kind:
            p = p.replace(f'<div class="panel {d["kind"]}"',
                          f'<div class="panel {d["kind"]} active"', 1)
        panels.append(p)

    html = HTML_TEMPLATE
    html = html.replace("__GENERATED_AT__", datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
    html = html.replace("__TABS__", "".join(tabs))
    html = html.replace("__PANELS__", "".join(panels))
    return html


# ==================== 主流程 ====================

ALL_KINDS = ("ssq", "dlt", "plw", "sd", "qxc")


def run_kind(kind: str, issue_count: int) -> dict:
    cfg = CONFIG[kind]
    draws = fetch(kind, issue_count)
    print(f"  [{cfg['name']}] 数据来源: {cfg.get('_source', '未知')}  期数: {len(draws)}", flush=True)
    return analyze(kind, draws)


def parse_args(argv: list) -> tuple:
    kinds = list(ALL_KINDS)
    issue_count = 15
    for a in (x.lower() for x in argv):
        if a in ALL_KINDS:
            kinds = [a]
        elif a == "all":
            kinds = list(ALL_KINDS)
        elif a.isdigit():
            issue_count = int(a)
    return kinds, issue_count


def main() -> int:
    kinds, issue_count = parse_args(sys.argv[1:])
    ordered = [k for k in ALL_KINDS if k in kinds]

    print("=" * 54, flush=True)
    print("  五彩种走势分析", flush=True)
    print("=" * 54, flush=True)

    reports = []
    for kind in ordered:
        print(f"\n--- 分析 {CONFIG[kind]['name']} ---", flush=True)
        try:
            reports.append(run_kind(kind, issue_count))
        except Exception as e:
            print(f"  [error] {CONFIG[kind]['name']} 分析失败: {e}", flush=True)

    if not reports:
        print("❌ 所有彩种均失败，未生成报告", flush=True)
        return 1

    out_path = Path(__file__).resolve().parent / "lottery_report.html"
    out_path.write_text(render_html(reports), encoding="utf-8")

    print(f"\n✅ 报告已生成: {out_path}", flush=True)
    print("程序执行完毕", flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())