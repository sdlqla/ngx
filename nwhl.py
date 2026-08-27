import re
import requests

# 1. 资源地址
GUOVIN_M3U_URL = (
    "https://raw.githubusercontent.com/Guovin/iptv-api/gd/output/result.m3u"
)
OLD_TXT_URL = "https://www.xn--rgv465a.top/live/Daily.txt"


def normalize_group_name(group_str):
    """清理 Emoji 和符号，并将分类统一清洗重命名"""
    # 移除表情和特殊符号，只保留汉字、字母和数字
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


# 存储分类数据：{ "广东频道": [ ("广东珠江", "http://..."), ... ] }
grouped_data = {}


def add_channel(group, name, url):
    """统一添加并归类频道"""
    clean_group = normalize_group_name(group)
    if not clean_group or not name or not url:
        return
    if clean_group not in grouped_data:
        grouped_data[clean_group] = []
    grouped_data[clean_group].append((name, url))


def parse_m3u(content):
    """解析 M3U 格式"""
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
                add_channel(current_group, current_name, line)


def parse_txt(content):
    """解析 TXT 格式"""
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
            add_channel(current_group, name, url)


# --- 1. 抓取并解析 Guovin 源 ---
print("正在获取 Guovin M3U 源...")
try:
    res1 = requests.get(GUOVIN_M3U_URL, timeout=15)
    if res1.status_code == 200:
        parse_m3u(res1.text)
except Exception as e:
    print(f"获取 Guovin 源失败: {e}")

# --- 2. 抓取并解析旧源 ---
print("正在合并旧 TXT 源...")
try:
    res2 = requests.get(OLD_TXT_URL, timeout=15)
    if res2.status_code == 200:
        parse_txt(res2.text)
except Exception as e:
    print(f"获取旧源失败/跳过: {e}")

# --- 3. 按照固定顺序去重并导出 ---
OUTPUT_ORDER = ["央视频道", "卫视频道", "广东频道", "港澳台"]

print("正在清洗合并并生成 my.txt...")
with open("my.txt", "w", encoding="utf-8") as f:
    for group in OUTPUT_ORDER:
        if group in grouped_data and grouped_data[group]:
            f.write(f"{group},#genre#\n")

            seen_pairs = set()
            for name, url in grouped_data[group]:
                if (name, url) not in seen_pairs:
                    seen_pairs.add((name, url))
                    f.write(f"{name},{url}\n")

            f.write("\n")

print("更新完成！")
