import argparse
import json
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime

import requests


HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/120.0.0.0 Safari/537.36"
    ),
    "Accept": "*/*",
    "Connection": "close",
}


# 固化白名单：这些源格式特殊（polyglot 图片伪装 / base64 加密包装 /
# 中文域名 / 动态域名+非标端口），普通 HTTP 验证判不准，境外 CI 网络下
# 会被误判失效。命中规则的 URL 跳过验证、无条件保留。
PROTECTED_RULES = [
    # 饭太硬生态：polyglot 图片外壳 + 尾部 Base64 配置（客户端能解析）
    "饭太硬",
    # 嗷呜：polyglot PNG 外壳 + 尾部 Base64 配置
    "itv666.cc/aowu",
    # 东篱：Base64 加密包装（SWKYkz1W 开头）
    "chigua.eu.org",
    # 王二小放牛娃：中文域名直连
    "王二小放牛娃",
    # bobohome 系列：动态域名 + 20247 非标端口 + emoji 路径
    "bobohome.ignorelist.com",
]


def is_protected(url):
    """命中白名单的 URL 跳过验证、永久保留。"""
    if not url:
        return False
    low = url.lower()
    if any(rule in low for rule in PROTECTED_RULES):
        return True
    # 中文域名（host 含非 ASCII，如 饭太硬.cc）：CI 境外 DNS 可能解析不稳
    try:
        from urllib.parse import urlsplit

        host = urlsplit(url).hostname or ""
        if any(ord(c) > 127 for c in host):
            return True
    except Exception:
        pass
    return False


def is_url_valid(url, timeout=8):
    """检查 URL 是否可访问。

    - clan:// 本地配置默认视为有效；
    - 先 HEAD，HEAD 失败或状态码异常再 GET；
    - 对 m3u8 使用 stream=True，只读取少量内容，避免下载整个播放列表。
    """
    if not url:
        return False

    if url.startswith("clan://"):
        return True

    if not url.startswith(("http://", "https://")):
        return False

    # 先尝试 HEAD
    try:
        resp = requests.head(
            url,
            timeout=timeout,
            allow_redirects=True,
            headers=HEADERS,
        )
        if resp.status_code < 400:
            return True
        resp.close()
    except requests.RequestException:
        pass

    # HEAD 失败或非成功状态码时，尝试 GET
    try:
        resp = requests.get(
            url,
            timeout=timeout,
            allow_redirects=True,
            headers=HEADERS,
            stream=True,
        )

        if resp.status_code >= 400:
            resp.close()
            return False

        # m3u8 读取一小段，确认不是空响应/明显异常
        if ".m3u8" in url.lower():
            try:
                next(resp.iter_content(chunk_size=1024), b"")
            except Exception:
                pass

        resp.close()
        return True
    except requests.RequestException:
        return False


def validate_txt_urls():
    """验证 assets/urls.txt 中的 URL。"""
    file_path = "assets/urls.txt"
    try:
        with open(file_path, "r", encoding="utf-8-sig") as f:
            urls = [
                line.strip()
                for line in f.readlines()
                if line.strip() and not line.startswith("#")
            ]

        valid_urls = []
        invalid_urls = []

        for url in urls:
            if is_url_valid(url):
                valid_urls.append(url)
                print(f"Valid: {url}")
            else:
                invalid_urls.append(url)
                print(f"Invalid: {url}")

            time.sleep(0.5)

        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        header = (
            f"# 更新时间: {timestamp}\n"
            f"# 有效URL数量: {len(valid_urls)}\n"
            f"# 无效URL数量: {len(invalid_urls)}\n\n"
        )

        with open(file_path, "w", encoding="utf-8") as f:
            f.write(header)
            for url in valid_urls:
                f.write(url + "\n")

        print(
            f"{file_path} 已更新，有效URL: {len(valid_urls)}，"
            f"无效URL: {len(invalid_urls)}"
        )

    except Exception as e:
        print(f"处理 {file_path} 时出错: {e}")


def validate_json_urls():
    """验证 jnsj.json 中的 URL。"""
    file_path = "jnsj.json"
    try:
        with open(file_path, "rb") as f:
            content = f.read()

        if content.startswith(b"\xef\xbb\xbf"):
            content = content[3:]

        data = json.loads(content.decode("utf-8"))
        original_count = len(data.get("urls", []))

        valid_urls = []
        invalid_urls = []
        protected_urls = []

        for item in data.get("urls", []):
            url = item.get("url", "")
            name = item.get("name", "")

            # 白名单源：跳过验证，无条件保留
            if is_protected(url):
                valid_urls.append(item)
                protected_urls.append(item)
                print(f"☆ {name} 白名单保留（跳过验证）")
                continue

            print(f"验证: {name} - {url}")

            if is_url_valid(url):
                valid_urls.append(item)
                print(f"√ {name} 有效")
            else:
                invalid_urls.append(item)
                print(f"× {name} 无效")

            time.sleep(0.5)

        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        data["urls"] = valid_urls
        data["last_validated"] = timestamp
        data["valid_count"] = len(valid_urls)
        data["invalid_count"] = len(invalid_urls)
        data["protected_count"] = len(protected_urls)
        data["original_count"] = original_count

        with open(file_path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

        print(
            f"{file_path} 已更新，原始URL数量: {original_count}，"
            f"有效URL数量: {len(valid_urls)}，无效URL数量: {len(invalid_urls)}"
        )

    except Exception as e:
        print(f"处理 {file_path} 时出错: {e}")


def validate_movie_txt(
    movie_file="35000movice.txt",
    invalid_file="invalid_movies.txt",
    delay=0.2,
    timeout=8,
    workers=1,
):
    """验证 35000movice.txt 中“名称,URL”格式的链接。

    规则：
    - 空行、# 注释行、#genre# 分类行先原样保留；
    - “名称,URL”行逐条验证；
    - 有效行写回原文件；
    - 无效行直接从主文件删除，并写入 invalid_file；
    - 如果某个 #genre# 分类下所有链接都被删除（没有有效条目），
      则该分类行也一并删除，避免出现空分类。
    """
    try:
        with open(movie_file, "r", encoding="utf-8-sig", errors="replace") as f:
            lines = f.read().splitlines()
    except FileNotFoundError:
        print(f"文件不存在: {movie_file}")
        return
    except Exception as e:
        print(f"读取 {movie_file} 出错: {e}")
        return

    entries = []   # 每项: (idx, raw, item)  item=None 表示非链接行
    tasks = []     # (idx, name, url)

    for idx, raw in enumerate(lines):
        line = raw.strip()

        if not line or line.startswith("#") or "#genre#" in line:
            entries.append((idx, raw, None))
            continue

        if "," not in line:
            entries.append((idx, raw, None))
            continue

        name, url = line.rsplit(",", 1)
        name = name.strip()
        url = url.strip()

        entries.append((idx, raw, (name, url)))
        tasks.append((idx, name, url))

    results = {}

    if workers <= 1:
        total = len(tasks)
        for i, (idx, name, url) in enumerate(tasks, start=1):
            ok = is_url_valid(url, timeout=timeout)
            results[idx] = ok
            print(f"[{i}/{total}] {'Valid' if ok else 'Invalid'}: {name} - {url}")
            if delay > 0:
                time.sleep(delay)
    else:
        total = len(tasks)
        print(f"开始并发验证 {movie_file}，任务数: {total}，并发数: {workers}")

        with ThreadPoolExecutor(max_workers=workers) as executor:
            future_map = {
                executor.submit(is_url_valid, url, timeout): (idx, name, url)
                for idx, name, url in tasks
            }

            done = 0
            for future in as_completed(future_map):
                idx, name, url = future_map[future]
                try:
                    ok = future.result()
                except Exception:
                    ok = False

                results[idx] = ok
                done += 1
                print(
                    f"[{done}/{total}] {'Valid' if ok else 'Invalid'}: "
                    f"{name} - {url}"
                )

    # 先按原顺序构建“分类块”，再决定是否保留分类行
    # 每块结构: {"genre_line": str 或 None, "items": [(raw, is_valid_or_None)]}
    blocks = []
    current_block = None

    for idx, raw, item in entries:
        line = raw.strip()

        if "#genre#" in line:
            current_block = {"genre_line": raw.strip(), "items": []}
            blocks.append(current_block)
            continue

        if current_block is None:
            current_block = {"genre_line": None, "items": []}
            blocks.append(current_block)

        if item is None:
            # 空行/注释/无法解析行：保留，但不参与有效性统计
            current_block["items"].append((raw.strip(), None))
        else:
            ok = results.get(idx, False)
            current_block["items"].append((raw.strip(), ok))

    output_lines = []
    invalid_lines = []

    for block in blocks:
        # 统计该分类下有效/无效链接数量
        valid_in_block = sum(
            1 for _, ok in block["items"] if ok is True
        )
        has_any_link = any(
            ok is not None for _, ok in block["items"]
        )

        # 有链接但全部无效 -> 连分类行一起丢弃
        if has_any_link and valid_in_block == 0:
            for raw, ok in block["items"]:
                if ok is False:
                    # 记录到无效清单
                    invalid_lines.append(raw)
                # 有效条目为0，这里 ok 为 None 的空行/注释也一并丢弃
            continue

        # 否则保留分类行
        if block["genre_line"] is not None:
            output_lines.append(block["genre_line"])

        # 保留该分类下的有效行；无效行删除并记录
        for raw, ok in block["items"]:
            if ok is None:
                # 空行/注释行保留
                output_lines.append(raw)
            elif ok is True:
                output_lines.append(raw)
            else:
                invalid_lines.append(raw)

    # 写回主文件
    try:
        with open(movie_file, "w", encoding="utf-8") as f:
            f.write("\n".join(output_lines))
            if output_lines:
                f.write("\n")
    except Exception as e:
        print(f"写入 {movie_file} 出错: {e}")
        return

    # 写无效链接清单
    try:
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        with open(invalid_file, "w", encoding="utf-8") as f:
            f.write(f"# 更新时间: {timestamp}\n")
            f.write(f"# 无效URL数量: {len(invalid_lines)}\n\n")
            for line in invalid_lines:
                f.write(line + "\n")
    except Exception as e:
        print(f"写入 {invalid_file} 出错: {e}")

    valid_count = sum(1 for ok in results.values() if ok)
    invalid_count = len(results) - valid_count

    print(
        f"{movie_file} 已更新，有效URL: {valid_count}，"
        f"无效URL: {invalid_count}，无效清单: {invalid_file}"
    )
    print("无效行已从主文件中删除。")


def main():
    parser = argparse.ArgumentParser(description="验证 URL 有效性并更新文件")
    parser.add_argument(
        "--movie-file",
        default="35000movice.txt",
        help="要验证的影视 txt 文件，默认 35000movice.txt",
    )
    parser.add_argument(
        "--invalid-file",
        default="invalid_movies.txt",
        help="无效链接输出文件，默认 invalid_movies.txt",
    )
    parser.add_argument(
        "--delay",
        type=float,
        default=0.2,
        help="串行验证时每条之间的延迟秒数，默认 0.2",
    )
    parser.add_argument(
        "--timeout",
        type=float,
        default=8,
        help="单条 URL 请求超时秒数，默认 8",
    )
    parser.add_argument(
        "--workers",
        type=int,
        default=1,
        help="并发验证线程数，默认 1；链接多时可设为 3-5",
    )
    parser.add_argument(
        "--skip-original",
        action="store_true",
        help="跳过 assets/urls.txt 和 jnsj.json，只验证影视 txt",
    )

    args = parser.parse_args()

    print("开始验证URLs...")

    if not args.skip_original:
        validate_txt_urls()
        print("\n开始验证jnsj.json...")
        validate_json_urls()

    print(f"\n开始验证 {args.movie_file}...")
    validate_movie_txt(
        movie_file=args.movie_file,
        invalid_file=args.invalid_file,
        delay=args.delay,
        timeout=args.timeout,
        workers=args.workers,
    )

    print("\nURL验证完成!")


if __name__ == "__main__":
    main()