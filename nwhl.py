import re
import requests

GUOVIN_URL = (
    "https://raw.githubusercontent.com/Guovin/iptv-api/gd/output/result.m3u"
)
DAILY_URL = "https://www.xn--rgv465a.top/live/Daily.txt"

# 港澳台及海外频道的扫描关键字（涵盖分类名与频道名）
HK_KEYWORDS = [
    "港",
    "台",
    "澳",
    "TVB",
    "翡翠",
    "明珠",
    "凤凰",
    "HBO",
    "TVBS",
    "中天",
    "东森",
    "三立",
    "星空",
    "美亚",
    "天映",
    "华视",
    "台视",
    "中视",
    "民视",
    "纬来",
    "J2",
    "莲花",
    "澳亚",
    "年代",
    "AXN",
    "DISCOVERY",
    "FOX",
    "CNN",
    "BBC",
]

# 1. 抓取并解析 Daily.txt（直接扫描频道名，确保图2中的 TVB翡翠、TVB明珠 100% 被捕获）
daily_hk_channels = []

try:
    r_daily = requests.get(DAILY_URL, timeout=15)
    r_daily.encoding = "utf-8"
    if r_daily.status_code == 200:
        current_cat = ""
        for line in r_daily.text.splitlines():
            line = line.strip()
            if not line:
                continue

            if "#genre#" in line:
                current_cat = line.split(",")[0].strip()
            elif "," in line:
                parts = line.split(",", 1)
                ch_name = parts[0].strip()
                ch_url = parts[1].strip()

                # 分类名 或 频道名 只要包含关键字，就强行放入港澳台
                combined = f"{current_cat} {ch_name}".upper()
                if any(k.upper() in combined for k in HK_KEYWORDS):
                    daily_hk_channels.append((ch_name, ch_url))

        print(f"Daily.txt 提取到港澳台频道 {len(daily_hk_channels)} 条")
except Exception as e:
    print(f"Daily.txt 获取失败: {e}")


# 2. 抓取并解析 Guovin 源
guovin_data = {"央视频道": [], "卫视频道": [], "广东频道": [], "港澳台": []}

try:
    r_guovin = requests.get(GUOVIN_URL, timeout=15)
    if r_guovin.status_code == 200:
        current_group, current_name = "", ""
        for line in r_guovin.text.splitlines():
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
                        k.upper() in (g_clean + n_clean).upper()
                        for k in HK_KEYWORDS
                    ):
                        guovin_data["港澳台"].append((current_name, line))
except Exception as e:
    print(f"Guovin 获取失败: {e}")


# 3. 按照优先级合并并输出 my.txt
with open("my.txt", "w", encoding="utf-8") as f:
    # 前三个分类优先使用 Guovin
    for group in ["央视频道", "卫视频道", "广东频道"]:
        if guovin_data[group]:
            f.write(f"{group},#genre#\n")
            seen = set()
            for name, url in guovin_data[group]:
                if (name, url) not in seen:
                    seen.add((name, url))
                    f.write(f"{name},{url}\n")
            f.write("\n")

    # 港澳台：Daily.txt 排最前面，Guovin 补在后面
    combined_hk = daily_hk_channels + guovin_data["港澳台"]
    if combined_hk:
        f.write("港澳台,#genre#\n")
        seen = set()
        for name, url in combined_hk:
            if (name, url) not in seen:
                seen.add((name, url))
                f.write(f"{name},{url}\n")
        f.write("\n")

print("my.txt 生成完成！")
