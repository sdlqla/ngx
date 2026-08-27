import requests

url = "https://www.xn--rgv465a.top/live/Daily.txt"

# 1. 想【整组保留】的大类关键字（匹配到的分类，里面的频道全要）
target_categories = ["卫视频道", "央视频道", "广东频道"]

# 2. 想【单独挑选】的具体频道关键字（即使大类没全要，只要包含这些名字也保留，并自动归到原分类下）
target_channels = ["TVB翡翠台", "TVB明珠台"]

response = requests.get(url)
lines = response.text.splitlines()

# 用于按分类存储频道的字典
grouped_data = {}
current_category_line = "其他频道,#genre#"

for line in lines:
    line = line.strip()
    if not line:
        continue

    # 1. 遇到分类标签行（带有 #genre#）
    if "#genre#" in line:
        current_category_line = line
        if current_category_line not in grouped_data:
            grouped_data[current_category_line] = []

    # 2. 普通频道行
    else:
        category_name = current_category_line.split(",")[0].strip()

        # 判断条件 A：当前分类名在“整组保留”列表中
        is_category_match = any(
            cat in category_name for cat in target_categories
        )

        # 判断条件 B：频道名字在“单独挑选”列表中
        is_channel_match = any(ch in line for ch in target_channels)

        # 满足任意条件就保留
        if is_category_match or is_channel_match:
            if current_category_line not in grouped_data:
                grouped_data[current_category_line] = []
            grouped_data[current_category_line].append(line)

# 3. 重新组装 TXT 内容（自动过滤掉没有频道的空分类）
output_lines = []
for cat_line, channel_list in grouped_data.items():
    if channel_list:  # 只有该分类下有符合条件的内容时才输出
        output_lines.append(cat_line)  # 保留小分类标题
        output_lines.extend(channel_list)  # 保留对应的频道

# 保存为 txt 文件
with open("my.txt", "w", encoding="utf-8") as f:
    f.write("\n".join(output_lines))

print("完美保留分类并提取完毕！")
