# -*- coding: utf-8 -*-
"""
五彩种自动分析脚本 (双色球 + 大乐透 + 排列五 + 福彩3D + 七星彩)
运行后生成 HTML 网页报告

- 双色球: 中国福彩官网实时接口
- 大乐透: 500.com 镜像XML(主源) + 中国体彩官网(备选)
- 排列五 / 福彩3D / 七星彩: 500.com 镜像XML
- 抓取成功自动写入本地缓存 lottery_cache/*.json
- 数据源失败自动降级：实时 → 本地缓存 → 内置静态数据
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
import os
import random
import sys
from collections import Counter
from datetime import datetime
from pathlib import Path

try:
    import requests
except ImportError:
    requests = None

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)",
    "Referer": "https://webapi.sporttery.cn/",
    "Accept": "application/json",
}

TABLE_SHOW = 5

# 数字型彩种每位颜色（按位从左到右）
DIGIT_COLORS = {
    "sd":  ["#e74c3c", "#e67e22", "#27ae60"],
    "plw": ["#e74c3c", "#e67e22", "#27ae60", "#2980b9", "#8e44ad"],
    "qxc": ["#e74c3c", "#e67e22", "#f39c12", "#27ae60", "#16a085", "#2980b9", "#8e44ad"],
}

CONFIG = {
    "ssq": {
        "name": "双色球", "code": "ssq", "source": "cwl",
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
        "name": "大乐透", "code": "dlt", "source": "500", "game_no": "350102",
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


def _save_cache(code: str, draws: list[tuple]) -> None:
    try:
        CACHE_DIR.mkdir(exist_ok=True)
        items = []
        for d in draws:
            if len(d) == 4:
                n, dt, f, b = d
                items.append({"issue": n, "date": dt, "front": list(f), "back": list(b)})
            elif len(d) == 3:
                n, dt, nums = d
                items.append({"issue": n, "date": dt, "nums": list(nums)})
        payload = {
            "updated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "draws": items,
        }
        _cache_path(code).write_text(
            json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8"
        )
    except Exception as e:
        print(f"  [warn] 写入缓存失败({code}): {e}", flush=True)


def _load_cache(code: str, issue_count: int) -> tuple[list[tuple] | None, str]:
    p = _cache_path(code)
    if not p.exists():
        return None, ""
    try:
        payload = json.loads(p.read_text(encoding="utf-8"))
        draws = []
        for x in payload.get("draws", []):
            if "nums" in x:
                draws.append((str(x["issue"]), str(x["date"]),
                              [int(v) for v in x["nums"]]))
            else:
                draws.append((str(x["issue"]), str(x["date"]),
                              [int(v) for v in x["front"]],
                              [int(v) for v in x["back"]]))
        if not draws:
            return None, ""
        return draws[-issue_count:], payload.get("updated_at", "")
    except Exception as e:
        print(f"  [warn] 读取缓存失败({code}): {e}", flush=True)
        return None, ""


# ==================== 数据抓取 ====================

def _norm_date(s: str) -> str:
    return (s or "").split("(")[0].strip()


def fetch_ssq(issue_count: int) -> list[tuple]:
    if requests is None:
        raise RuntimeError("未安装 requests")
    url = "https://www.cwl.gov.cn/cwl_admin/front/cwlkj/search/kjxx/findDrawNotice"
    params = {"name": "ssq", "issueCount": str(issue_count)}
    r = requests.get(url, params=params, headers=HEADERS, timeout=15)
    r.raise_for_status()

    draws = []
    for item in r.json().get("result", [])[:issue_count]:
        reds = [int(x) for x in (item.get("red") or "").split(",") if x]
        blue_raw = item.get("blue") or ""
        if not reds or not blue_raw:
            continue
        try:
            blue = int(blue_raw)
        except ValueError:
            continue
        num = item.get("code") or item.get("issueno") or ""
        draws.append((str(num), _norm_date(item.get("date") or ""), reds, [blue]))

    if not draws:
        raise ValueError("福彩接口未解析到双色球数据")
    draws.reverse()
    return draws


def _parse_dlt_xml(text: str, issue_count: int) -> list[tuple]:
    from xml.etree import ElementTree as ET
    root = ET.fromstring(text)
    draws = []
    for row in root.findall("row"):
        opencode = row.get("opencode", "")
        if "|" not in opencode:
            continue
        front_s, back_s = opencode.split("|", 1)
        try:
            front = [int(x) for x in front_s.split(",") if x]
            back = [int(x) for x in back_s.split(",") if x]
        except ValueError:
            continue
        if len(front) != 5 or len(back) != 2:
            continue
        draws.append((row.get("expect", ""), (row.get("opentime") or "")[:10], front, back))
        if len(draws) >= issue_count:
            break

    if not draws:
        raise ValueError("500.com XML 未解析到大乐透数据")
    return draws


def fetch_dlt(issue_count: int) -> tuple[list[tuple], str]:
    if requests is None:
        raise RuntimeError("未安装 requests")

    url500 = "https://datachart.500.com/static/info/kaijiang/xml/dlt/list.xml"
    h500 = dict(HEADERS)
    h500.update({"Referer": "https://datachart.500.com/dlt/history/", "Accept": "*/*"})
    try:
        r = requests.get(url500, headers=h500, timeout=15)
        r.raise_for_status()
        draws = _parse_dlt_xml(r.text, issue_count)
        draws.reverse()
        return draws, "500.com 镜像(实时)"
    except Exception as e:
        print(f"  [info] 500.com 源失败({e}), 尝试体彩官网...", flush=True)

    url = "https://webapi.sporttery.cn/gateway/lottery/getHistoryPageListV1.qry"
    params = {
        "gameNo": CONFIG["dlt"]["game_no"],
        "provinceId": "0",
        "pageSize": str(issue_count),
        "isVerify": "1",
        "pageNo": "1",
    }
    dlt_headers = dict(HEADERS)
    dlt_headers.update({"Origin": "https://webapi.sporttery.cn",
                        "Cookie": "Hm_lvt_=1; Hm_lpvt_=1"})
    r = requests.get(url, params=params, headers=dlt_headers, timeout=15)
    r.raise_for_status()
    data = r.json().get("value", {}).get("list", [])

    draws = []
    for item in data[:issue_count]:
        if "排列" in (item.get("lotteryGameName") or ""):
            continue
        nums = [n for n in (item.get("lotteryDrawResult") or "").split()
                if n not in ("+", "＋")]
        if len(nums) < 7:
            continue
        try:
            front = [int(x) for x in nums[:5]]
            back = [int(x) for x in nums[5:7]]
        except ValueError:
            continue
        draws.append((item.get("lotteryDrawNum"), item.get("lotteryDrawTime"), front, back))

    if not draws:
        raise ValueError(f"未解析到大乐透数据(gameNo={CONFIG['dlt']['game_no']})")
    return draws, "中国体彩官网(实时)"


def _parse_digit_xml(text: str, issue_count: int, digits: int) -> list[tuple]:
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


def fetch_digit(kind: str, issue_count: int) -> tuple[list[tuple], str]:
    if requests is None:
        raise RuntimeError("未安装 requests")
    cfg = CONFIG[kind]
    url = f"https://datachart.500.com/static/info/kaijiang/xml/{kind}/list.xml"
    h = dict(HEADERS)
    h.update({"Referer": f"https://datachart.500.com/{kind}/history/", "Accept": "*/*"})
    r = requests.get(url, headers=h, timeout=15)
    r.raise_for_status()
    draws = _parse_digit_xml(r.text, issue_count, cfg["digits"])
    draws.reverse()
    return draws, "500.com 镜像(实时)"


def fetch(kind: str, issue_count: int) -> list[tuple]:
    cfg = CONFIG[kind]
    code = cfg["code"]

    try:
        if requests is None:
            raise RuntimeError("未安装 requests")
        if cfg["source"] == "cwl":
            draws, source = fetch_ssq(issue_count), "中国福彩官网(实时)"
        elif cfg["source"] == "500":
            draws, source = fetch_dlt(issue_count)
        elif cfg["source"] in ("500plw", "500sd", "500qxc"):
            draws, source = fetch_digit(kind, issue_count)
        else:
            raise RuntimeError(f"未知数据源: {cfg['source']}")
        if not draws:
            raise ValueError("返回为空")

        _save_cache(code, draws)
        cfg["_source"] = source
        cfg["_source_cls"] = "source-live"
        return draws
    except Exception as e:
        print(f"  [warn] 实时接口失败({cfg['name']}: {e})，尝试读取本地缓存...", flush=True)

    cached, updated_at = _load_cache(code, issue_count)
    if cached:
        tail = f" {updated_at}" if updated_at else ""
        cfg["_source"] = f"本地缓存(上次实时:{tail})" if tail else "本地缓存"
        cfg["_source_cls"] = "source-cache"
        return cached

    cfg["_source"] = "内置静态数据(非实时)"
    cfg["_source_cls"] = "source-static"
    print(f"  [warn] {cfg['name']} 缓存不可用，使用内置静态数据兜底", flush=True)
    return list(cfg["static"][:issue_count])


# ==================== 分析 ====================

def _zone_of(x: int, zones: list[tuple[int, int]]) -> int:
    for i, (a, b) in enumerate(zones):
        if a <= x <= b:
            return i
    return 0


def _pick_combo(rng: random.Random, priority: list[int], num_range: tuple[int, int],
                need: int, sum_range: tuple[int, int], zones: list[tuple[int, int]],
                max_tries: int = 500) -> list[int]:
    lo, hi = num_range
    prio = [x for x in dict.fromkeys(priority) if lo <= x <= hi]
    prio_set = set(prio)
    others = [x for x in range(lo, hi + 1) if x not in prio_set]

    def valid(cand: list[int]) -> bool:
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
                  last_front: list[int], hot: list[int], cold: list[int]) -> list[dict]:
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

    def back_slice(i: int) -> list[int]:
        return sorted(int(x) for x in back_sorted[i * bp:(i + 1) * bp])

    return [
        {"label": "热号型", "front": hot_combo,   "back": back_slice(0)},
        {"label": "邻号型", "front": neigh_combo, "back": back_slice(1)},
        {"label": "均衡型", "front": eq_combo,    "back": back_slice(2)},
    ]


def _analyze_lotto(kind: str, draws: list[tuple]) -> dict:
    cfg = CONFIG[kind]
    zones = cfg["zones"]
    num_range = cfg["front_range"]

    front_counter: Counter = Counter()
    back_counter: Counter = Counter()
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

    table = [{
        "issue": num,
        "date": (date or "").replace("-", ""),
        "front": front,
        "back": back,
        "front_zone": [_zone_of(x, zones) for x in front],
    } for num, date, front, back in draws]

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
    }


def _build_digit_combos(pos_counters: list[Counter], d_lo: int, d_hi: int,
                        digits: int) -> list[dict]:
    def ranked(counter: Counter) -> list[int]:
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


def _analyze_digit(kind: str, draws: list[tuple]) -> dict:
    cfg = CONFIG[kind]
    digits = cfg["digits"]
    d_lo, d_hi = cfg["digit_range"]

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

    table = [{
        "issue": issue,
        "date": (date or "").replace("-", ""),
        "nums": nums,
    } for issue, date, nums in draws]

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
    }


def analyze(kind: str, draws: list[tuple]) -> dict:
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
}
*{box-sizing:border-box;margin:0;padding:0}
body{font-family:"Microsoft YaHei","PingFang SC",-apple-system,sans-serif;
  background:var(--bg);color:#2c3e50;padding:16px;line-height:1.6;
  -webkit-text-size-adjust:100%}
.wrap{max-width:960px;margin:0 auto}
h1{text-align:center;font-size:22px;margin-bottom:6px}
.subtitle{text-align:center;color:#7f8c8d;font-size:12px;margin-bottom:18px}
.tabs{display:flex;gap:10px;justify-content:center;margin-bottom:18px;flex-wrap:wrap}
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
/* tag 行改成两端对齐，右边放复制按钮 */
.combo .tag{display:flex;justify-content:space-between;align-items:center;gap:8px;
  font-size:12px;color:#7f8c8d;margin-bottom:8px}
.combo .line{display:flex;align-items:center;flex-wrap:nowrap;white-space:nowrap}
.combo .sep{margin:0 6px;color:#bbb;font-weight:bold}
/* 复制按钮 */
.copy-btn{padding:2px 10px;border-radius:12px;border:1px solid #cbd5e0;
  background:#fff;color:#555;font-size:11px;font-weight:600;cursor:pointer;
  user-select:none;-webkit-tap-highlight-color:transparent;transition:.15s;
  font-family:inherit;line-height:1.6;white-space:nowrap;flex:none}
.copy-btn:hover{background:#eef2f7;border-color:#a0aec0}
.copy-btn:active{transform:scale(.96)}
.copy-btn.copied{background:#27ae60;border-color:#27ae60;color:#fff}
.note{background:#fff9e6;border:1px solid #ffe08a;border-radius:10px;padding:12px 16px;
  color:#8a6d00;font-size:12px;text-align:center;line-height:1.7}
.summary{display:flex;gap:16px;flex-wrap:wrap;font-size:12px;color:#555;margin-top:8px}
.summary b{color:#2c3e50}

@media(max-width:600px){
  body{padding:8px;font-size:13px}
  h1{font-size:18px;margin-bottom:4px}
  .subtitle{font-size:11px;line-height:1.5;margin-bottom:12px;padding:0 4px}
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
  .combo .tag{font-size:11px;margin-bottom:6px}
  .combo .sep{margin:0 4px;font-size:13px}
  .copy-btn{padding:3px 9px;font-size:10px}
  .note{padding:10px 12px;font-size:11px;line-height:1.6}
  .summary{font-size:11px;gap:8px;margin-top:6px}
}
</style>
</head>
<body>
<div class="wrap">
<h1>🎯 彩票走势分析</h1>
<div class="subtitle">生成时间：__GENERATED_AT__<br>数据来源：中国福彩官网 / 500.com 镜像 / 中国体彩官网 / 本地缓存</div>

<div class="tabs">
  __TABS__
</div>

__PANELS__

<div class="card">
  <div class="note">⚠️ 彩票为独立随机事件，走势不能预测未来。以上号码仅基于历史频率推演，<b>仅供娱乐参考，非投注建议</b>。请理性购彩、量力而行。</div>
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

/* ---- 复制功能：优先 Clipboard API，http 环境回退 execCommand ---- */
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


def _render_balls(front: list[int], front_zone: list[int], back: list[int]) -> str:
    parts = []
    for i, x in enumerate(front):
        z = front_zone[i] if i < len(front_zone) else 0
        parts.append(f'<span class="ball z{z}">{int(x):02d}</span>')
    if back:
        parts.append('<span class="ball-sep">+</span>')
        for x in back:
            parts.append(f'<span class="ball back">{int(x):02d}</span>')
    return "".join(parts)


def _copy_text_lotto(front: list[int], back: list[int]) -> str:
    s = " ".join(f"{int(x):02d}" for x in front)
    if back:
        s += " + " + " ".join(f"{int(x):02d}" for x in back)
    return s


def _copy_text_digit(nums: list[int], split_at) -> str:
    parts = [str(int(x)) for x in nums]
    if split_at is not None and 0 < split_at < len(parts):
        return " ".join(parts[:split_at]) + " + " + " ".join(parts[split_at:])
    return " ".join(parts)


def _render_panel_lotto(d: dict) -> str:
    kind = d["kind"]
    cls = "ssq" if kind == "ssq" else "dlt"
    source_cls = d.get("source_cls", "source-static")
    zones = d["zones"]

    recent = d["table"][-TABLE_SHOW:] if d["table"] else []
    last_issue = recent[-1]["issue"] if recent else None
    rows = []
    for row in recent:
        tr_cls = ' class="latest"' if row["issue"] == last_issue else ''
        balls_html = _render_balls(row["front"], row["front_zone"], row["back"])
        rows.append(
            f'<tr{tr_cls}>'
            f'<td>{row["issue"]}</td>'
            f'<td>{row["date"]}</td>'
            f'<td class="num-col">{balls_html}</td>'
            f'</tr>'
        )
    table_html = (
        '<table><thead><tr><th>期号</th><th>日期</th>'
        '<th class="num-col">号码</th></tr></thead>'
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
        combo_cards.append(
            f'<div class="combo {combo_cls[i]}">'
            f'<div class="tag">'
            f'<span>组合{i + 1} · {c["label"]}</span>'
            f'<button type="button" class="copy-btn" data-copy="{copy_text}">📋 复制</button>'
            f'</div>'
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
        combo_cards.append(
            f'<div class="combo {combo_cls[i]}">'
            f'<div class="tag">'
            f'<span>组合{i + 1} · {c["label"]}</span>'
            f'<button type="button" class="copy-btn" data-copy="{copy_text}">📋 复制</button>'
            f'</div>'
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


def render_html(reports: list[dict]) -> str:
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


def parse_args(argv: list[str]) -> tuple[list[str], int]:
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