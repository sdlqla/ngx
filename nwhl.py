import re
import requests

# 1. 资源地址
GUOVIN_M3U_URL = (
    "https://raw.githubusercontent.com/Guovin/iptv-api/gd/output/result.m3u"
)
OLD_TXT_URL = "https://www.xn--rgv465a.top/live/Daily.txt"


def normalize_group_name(group_str):
    """清理 Emoji 并统一分类名称"""
    cleaned = re.sub(r"[^\u4e00-\u9fa5a-zA-Z0-9]", "", group_str)

    if "央视" in cleaned:
        return "央视频道"
    elif "卫视" in cleaned:
        return "卫视频道"
    elif "广东" in cleaned:
        return "广东频道"
    elif any(
        k in cleaned for k in ["港", "澳", "台", "凤凰", "翡翠", "TVB", "HBO"]
    ):
        return "港澳台"
    else:
        return cleaned


def parse_m3u(content):
    """解析 Guovin 的 M3U 源"""
    data = {}
    lines = content.splitlines()
    current_group = "其他"
    current_name = ""

    for line in lines:
        line = line.strip()
        if line.startswith("#EXTINF"):
            group_match = re.search(r'group-title="([^"]+)"', line)
            current_group = group_match.group(1) if group_match else "其他"
            if "," in line:
                current_name = line.split(",")[-1].strip()
            else:
                current_name = "未知频道"
        elif line and not line.startswith("#"):
            if current_name:
                cg = normalize_group_name(current_group)
                if cg not in data:
                    data[cg] = []
                data[cg].append((current_name, line))
    return data


def parse_txt(content):
    """解析旧 TXT 源"""
    data = {}
    current_group = "其他"
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
            cg = normalize_group_name(current_group)
            if cg not in data:
                data[cg] = []
            data[cg].append((name, url))
    return data


# --- 1. 分别抓取并解析两个源 ---
guovin_data = {}
old_data = {}

print("正在获取 Guovin M3U 源...")
try:
    res1 = requests.get(GUOVIN_M3U_URL, timeout=15)
    if res1.status_code == 200:
        guovin_data = parse_m3u(res1.text)
except Exception as e:
    print(f"获取 Guovin 源失败: {e}")

print("正在获取旧 TXT 源...")
try:
    res2 = requests.get(OLD_TXT_URL, timeout=15)
    if res2.status_code == 200:
        old_data = parse_txt(res2.text)
except Exception as e:
    print(f"获取旧源失败: {e}")

# --- 2. 按自定义优先级合并并导出 ---
OUTPUT_ORDER = ["央视频道", "卫视频道", "广东频道", "港澳台"]

print("正在按优先级去重合并并生成 my.txt...")
with open("my.txt", "w", encoding="utf-8") as f:
    for group in OUTPUT_ORDER:
        # 针对不同分类设定不同的主辅优先级
        if group == "港澳台":
            # 港澳台：旧 TXT 为主，Guovin 为辅
            primary_list = old_data.get(group, [])
            secondary_list = guovin_data.get(group, [])
        else:
            # 央视/卫视/广东：Guovin 为主，旧 TXT 为辅
            primary_list = guovin_data.get(group, [])
            secondary_list = old_data.get(group, [])

        combined_list = primary_list + secondary_list

        if combined_list:
            f.write(f"{group},#genre#\n")
            seen_pairs = set()
            for name, url in combined_list:
                if (name, url) not in seen_pairs:
                    seen_pairs.add((name, url))
                    f.write(f"{name},{url}\n")
            f.write("\n")

print("更新完成！")
