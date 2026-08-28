import re
import requests
from datetime import datetime, timedelta, timezone

GUOVIN_URL = "https://raw.githubusercontent.com/Guovin/iptv-api/gd/output/result.m3u"
DAILY_URL = "https://www.xn--rgv465a.top/live/Daily.txt"

def normalize_name(name):
    """把 'TVB翡翠' 和 '翡翠台' 统一命名为 '翡翠台'，实现完美合并"""
    if "翡翠" in name:
        return "翡翠台"
    if "明珠" in name:
        return "明珠台"
    return name.strip()


# 1. 从 Daily.txt 只抓取 TVB / 翡翠台 等港台频道（Daily 优先）
daily_hk = []
try:
    r_daily = requests.get(DAILY_URL, timeout=15)
    r_daily.encoding = "utf-8"
    if r_daily.status_code == 200:
        for line in r_daily.text.splitlines():
            line = line.strip()
            if not line or "#genre#" in line:
                continue
            if "," in line:
                parts = line.split(",", 1)
                ch_name = parts[0].strip()
                ch_url = parts[1].strip()

                # 匹配 Daily 里的 TVB、翡翠台、港台频道
                if any(k in ch_name.upper() for k in ["TVB", "翡翠", "明珠", "TVBS", "凤凰"]):
                    daily_hk.append((normalize_name(ch_name), ch_url))
        print(f"Daily.txt 获取到 TVB/港台频道 {len(daily_hk)} 条")
except Exception as e:
    print(f"Daily.txt 获取失败: {e}")


# 2. 从 Guovin 获取央视、卫视、广东（独占），以及精准匹配港台源（补充）
guovin_data = {"央视频道": [], "卫视频道": [], "广东频道": [], "港澳台": []}

try:
    r_guovin = requests.get(GUOVIN_URL, timeout=15)
    if r_guovin.status_code == 200:
        current_group, current_name, tvg_id = "", "", ""
        for line in r_guovin.text.splitlines():
            line = line.strip()
            if line.startswith("#EXTINF"):
                g_match = re.search(r'group-title="([^"]+)"', line)
                current_group = g_match.group(1) if g_match else ""

                id_match = re.search(r'tvg-id="([^"]+)"', line)
                tvg_id = id_match.group(1) if id_match else ""

                current_name = line.split(",")[-1].strip() if "," in line else ""

            elif line and not line.startswith("#"):
                if current_name:
                    g_clean = re.sub(r"[^\u4e00-\u9fa5a-zA-Z0-9]", "", current_group)
                    n_clean = re.sub(r"[^\u4e00-\u9fa5a-zA-Z0-9]", "", current_name)

                    if "央视" in g_clean or "CCTV" in n_clean.upper():
                        guovin_data["央视频道"].append((current_name, line))
                    elif "卫视" in g_clean:
                        guovin_data["卫视频道"].append((current_name, line))
                    elif "广东" in g_clean or "广州" in n_clean:
                        guovin_data["广东频道"].append((current_name, line))
                    elif (
                        tvg_id == "翡翠台"
                        or any(k in n_clean.upper() for k in ["TVB", "翡翠", "明珠", "TVBS", "凤凰"])
                        or any(k in g_clean for k in ["港澳台", "港台", "香港", "台湾"])
                    ):
                        guovin_data["港澳台"].append((normalize_name(current_name), line))
        print("Guovin 源获取完成")
except Exception as e:
    print(f"Guovin 获取失败: {e}")


# 3. 合并写入 my.txt (包含更新时间和频道去重)
beijing_tz = timezone(timedelta(hours=8))
update_time = datetime.now(beijing_tz).strftime("%Y-%m-%d %H:%M:%S")

with open("my.txt", "w", encoding="utf-8") as f:
    # 顶部添加更新时间
    f.write("🕒更新时间,#genre#\n")
    f.write(f"{update_time},#\n\n")

    # 写入 央视、卫视、广东（自带去重）
    for group in ["央视频道", "卫视频道", "广东频道"]:
        if guovin_data[group]:
            f.write(f"{group},#genre#\n")
            seen = set()
            for name, url in guovin_data[group]:
                if (name, url) not in seen:
                    seen.add((name, url))
                    f.write(f"{name},{url}\n")
            f.write("\n")

    # 写入港澳台（Daily 排前，Guovin 补后，自带去重）
    combined_hk = daily_hk + guovin_data["港澳台"]
    if combined_hk:
        f.write("港澳台,#genre#\n")
        seen = set()
        for name, url in combined_hk:
            if (name, url) not in seen:
                seen.add((name, url))
                f.write(f"{name},{url}\n")
        f.write("\n")

print("更新成功，my.txt 已生成。")
