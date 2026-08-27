import re
import requests

GUOVIN_URL = (
    "https://raw.githubusercontent.com/Guovin/iptv-api/gd/output/result.m3u"
)
DAILY_URL = "https://www.xn--rgv465a.top/live/Daily.txt"

# 港澳台及海外频道的识别关键字
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
]


def normalize_channel_name(name):
    """统一港澳台频道名称，解决 Daily 的 'TVB翡翠' 与 Guovin 的 '翡翠台' 名字不一致导致分离的问题"""
    n = name.strip()

    if "翡翠" in n:
        return "翡翠台"
    if "明珠" in n:
        return "明珠台"
    if "TVBS新闻" in n or "TVBS 新闻" in n:
        return "TVBS新闻台"
    if "TVBS亚洲" in n:
        return "TVBS亚洲台"
    if "TVBS综合" in n:
        return "TVBS综合台"
    if "凤凰中文" in n:
        return "凤凰中文台"
    if "凤凰资讯" in n:
        return "凤凰资讯台"
    if "凤凰香港" in n:
        return "凤凰香港台"
    if "J2" in n.upper():
        return "J2台"

    return n


# 1. 抓取并解析 Daily.txt（港澳台频道）
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

                combined = f"{current_cat} {ch_name}".upper()
                if any(k.upper() in combined for k in HK_KEYWORDS):
                    # 统一频道名字（TVB翡翠 -> 翡翠台）
                    norm_name = normalize_channel_name(ch_name)
                    daily_hk_channels.append((norm_name, ch_url))

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

                    norm_name = normalize_channel_name(current_name)

                    if "央视" in g_clean or "CCTV" in n_clean.upper():
                        guovin_data["央视频道"].append((norm_name, line))
                    elif "卫视" in g_clean:
                        guovin_data["卫视频道"].append((norm_name, line))
                    elif "广东" in g_clean or "广州" in n_clean:
                        guovin_data["广东频道"].append((norm_name, line))
                    elif any(
                        k.upper() in (g_clean + n_clean).upper()
                        for k in HK_KEYWORDS
                    ):
                        guovin_data["港澳台"].append((norm_name, line))
except Exception as e:
    print(f"Guovin 获取失败: {e}")


# 3. 按照优先级合并输出 my.txt
with open("my.txt", "w", encoding="utf-8") as f:
    # 央视、卫视、广东
    for group in ["央视频道", "卫视频道", "广东频道"]:
        if guovin_data[group]:
            f.write(f"{group},#genre#\n")
            seen = set()
            for name, url in guovin_data[group]:
                if (name, url) not in seen:
                    seen.add((name, url))
                    f.write(f"{name},{url}\n")
            f.write("\n")

    # 港澳台：Daily.txt 线路排前面，Guovin 线路紧跟在后
    combined_hk = daily_hk_channels + guovin_data["港澳台"]
    if combined_hk:
        f.write("港澳台,#genre#\n")
        seen = set()
        for name, url in combined_hk:
            if (name, url) not in seen:
                seen.add((name, url))
                f.write(f"{name},{url}\n")
        f.write("\n")

print("my.txt 更新完成！")
