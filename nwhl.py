import re
import requests

# 1. 资源地址
GUOVIN_M3U_URL = (
    "https://raw.githubusercontent.com/Guovin/iptv-api/gd/output/result.m3u"
)
OLD_TXT_URL = (
    "https://www.xn--rgv465a.top/live/Daily.txt"  # 之前使用的旧 TXT 源地址
)

# 2. 需要保留的分类关键字（匹配到的分类才会写入最终文件）
TARGET_CATEGORIES = ["央视", "卫视", "港澳台", "广东"]

# 存储分类数据：{ "央视频道": [ ("CCTV-1", "http://..."), ... ] }
grouped_data = {}


def parse_m3u(content):
    """解析 Guovin 的 M3U 格式源"""
    lines = content.splitlines()
    current_group = "其他频道"
    current_name = ""

    for line in lines:
        line = line.strip()
        if line.startswith("#EXTINF"):
            # 提取 group-title 分类名称
            group_match = re.search(r'group-title="([^"]+)"', line)
            if group_match:
                current_group = group_match.group(1)
            else:
                current_group = "其他频道"

            # 提取频道名称
            if "," in line:
                current_name = line.split(",")[-1].strip()
            else:
                current_name = "未知频道"

        elif line and not line.startswith("#"):
            # 当前行为播放链接 URL
            url = line
            if current_name:
                if current_group not in grouped_data:
                    grouped_data[current_group] = []
                # 记录频道与链接
                grouped_data[current_group].append((current_name, url))


def parse_txt(content):
    """解析旧的 TXT 格式源"""
    current_group = "其他频道"
    for line in content.splitlines():
        line = line.strip()
        if not line:
            continue
        if "#genre#" in line:
            current_group = line.split(",")[0].strip()
        elif "," in line:
            parts = line.split(",")
            name = parts[0].strip()
            url = parts[1].strip()
            if current_group not in grouped_data:
                grouped_data[current_group] = []
            grouped_data[current_group].append((name, url))


# --- 1. 抓取并解析 Guovin 源 ---
print("正在获取 Guovin M3U 源...")
try:
    res1 = requests.get(GUOVIN_M3U_URL, timeout=15)
    if res1.status_code == 200:
        parse_m3u(res1.text)
except Exception as e:
    print(f"获取 Guovin 源失败: {e}")

# --- 2. 抓取并合并旧源 ---
print("正在合并旧 TXT 源...")
try:
    res2 = requests.get(OLD_TXT_URL, timeout=15)
    if res2.status_code == 200:
        parse_txt(res2.text)
except Exception as e:
    print(f"获取旧源失败/跳过: {e}")

# --- 3. 去重并写入 my.txt ---
print("正在去重并生成 my.txt...")
with open("my.txt", "w", encoding="utf-8") as f:
    for group, channels in grouped_data.items():
        # 筛选包含目标关键字的分类
        if any(target in group for target in TARGET_CATEGORIES):
            f.write(f"{group},#genre#\n")

            # 双重去重：避免同一个频道名绑定完全相同的 URL
            seen_pairs = set()
            for name, url in channels:
                if (name, url) not in seen_pairs:
                    seen_pairs.add((name, url))
                    f.write(f"{name},{url}\n")

            f.write("\n")

print("更新完成！")
