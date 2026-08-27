import re
import requests

GUOVIN_URL = (
    "https://raw.githubusercontent.com/Guovin/iptv-api/gd/output/result.m3u"
)
DAILY_URL = "https://www.xn--rgv465a.top/live/Daily.txt"

# 1. 解析 Guovin (获取 央视、卫视、广东，以及港澳台备用)
guovin_data = {"央视频道": [], "卫视频道": [], "广东频道": [], "港澳台": []}

try:
    r1 = requests.get(GUOVIN_URL, timeout=15)
    if r1.status_code == 200:
        current_group, current_name = "", ""
        for line in r1.text.splitlines():
            line = line.strip()
            if line.startswith("#EXTINF"):
                g_match = re.search(r'group-title="([^"]+)"', line)
                current_group = g_match.group(1) if g_match else ""
                current_name = (
                    line.split(",")[-1].strip() if "," in line else ""
                )
            elif line and not line.startswith("#"):
                if current_name:
                    g_clean = re.sub(
                        r"[^\u4e00-\u9fa5a-zA-Z0-9]", "", current_group
                    )
                    n_clean = re.sub(
                        r"[^\u4e00-\u9fa5a-zA-Z0-9]", "", current_name
                    )

                    if "央视" in g_clean or "CCTV" in n_clean.upper():
                        guovin_data["央视频道"].append((current_name, line))
                    elif "卫视" in g_clean:
                        guovin_data["卫视频道"].append((current_name, line))
                    elif "广东" in g_clean or "广州" in n_clean:
                        guovin_data["广东频道"].append((current_name, line))
                    elif any(
                        k in (g_clean + n_clean).upper()
                        for k in ["港", "台", "澳", "TVB", "翡翠", "凤凰", "HBO"]
                    ):
                        guovin_data["港澳台"].append((current_name, line))
except Exception as e:
    print(f"Guovin 解析失败: {e}")

# 2. 解析 Daily.txt (沿用你原本的思想：精准识别 港台/翡翠 分类并全量提取)
daily_hk_channels = []
hk_targets = ["港台", "港澳", "台湾", "香港", "翡翠", "TVB", "凤凰"]

try:
    r2 = requests.get(DAILY_URL, timeout=15)
    if r2.status_code == 200:
        is_target_group = False
        for line in r2.text.splitlines():
            line = line.strip()
            if not line:
                continue

            # 遇到分类行，判断是否属于目标分类
            if "#genre#" in line:
                cat_name = line.split(",")[0].strip()
                is_target_group = any(k in cat_name for k in hk_targets)
            # 普通频道行，如果是目标分类则直接提取
            elif is_target_group and "," in line:
                parts = line.split(",", 1)
                daily_hk_channels.append((parts[0].strip(), parts[1].strip()))
except Exception as e:
    print(f"Daily.txt 解析失败: {e}")

# 3. 按顺序生成 my.txt
with open("my.txt", "w", encoding="utf-8") as f:
    # 写入央视、卫视、广东 (Guovin 源)
    for group in ["央视频道", "卫视频道", "广东频道"]:
        if guovin_data[group]:
            f.write(f"{group},#genre#\n")
            seen = set()
            for name, url in guovin_data[group]:
                if (name, url) not in seen:
                    seen.add((name, url))
                    f.write(f"{name},{url}\n")
            f.write("\n")

    # 写入港澳台 (Daily.txt 提取到的频道排最前面，Guovin 补在后面)
    combined_hk = daily_hk_channels + guovin_data["港澳台"]
    if combined_hk:
        f.write("港澳台,#genre#\n")
        seen = set()
        for name, url in combined_hk:
            if (name, url) not in seen:
                seen.add((name, url))
                f.write(f"{name},{url}\n")
        f.write("\n")

print("更新完成！")
