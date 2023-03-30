# 1. 输入为一个BV号
# 2. 工作流程为:
#    1. 解析并下载视频
#    2. 生成一个视频信息的json文件

import os
import shutil
import requests
import time
import random
import sys
import json

# 默认的save_path位置为 ..\data\当前的时间戳加上一串随机数 文件夹
save_path = os.path.join(os.path.pardir, 'data',
                         f'{int(time.time())}{random.randint(100000, 999999)}')

INDEX_PATH = r"../index.json"

RETRY = 3

ERR_LOG = """<h1>错误报告</h1>
<hr>
<p> 很不幸的通知您，您申请备份的视频中有一些视频下载失败了。</p>
<p> 详细信息如下：</p>
<p> 视频BV号：{bv}</p>
<p> 失败的P数：{err_list}</p>
<p> 以上视频在我们尝试了{retry}次后仍然无法正常下载。请您检查一下视频是否已经被删除，或者视频是否为付费视频。</p>
<br>
<p> Web Archive Team</p>
<p> {date}</p>
"""

FINISHED_LOG = """<h1>备份完成</h1>
<hr>
<p> 您申请备份的视频已经全部备份完成。</p>
<p> 详细信息如下：</p>
<p> 视频BV号：{bv}</p>
<p> 视频标题：{title}</p>
<p> 视频简介：{desc}</p>
<p> 视频发布时间：{pubtime}</p>
<p> 视频作者：{owner}</p>
<br>
<p> Web Archive Team</p>
<p> {date}</p>
"""


def download_video(bv, part=[], retry=3):
    err_list = []

    if not os.path.exists(save_path):
        os.makedirs(save_path)

    if not os.path.exists(os.path.join(os.path.pardir, 'temp')):
        os.makedirs(os.path.join(os.path.pardir, 'temp'))

    api_url = f"https://api.bilibili.com/x/web-interface/view?bvid={bv}"
    response = requests.get(api_url)
    data = response.json()["data"]
    title = data["title"]
    desc = data["desc"]
    pubtime = data["pubdate"]
    owner = data["owner"]

    # 获取分P标题，为一个数组
    # 如果只有一个P，那么就是一个空数组
    parts = data["pages"]

    total_number = video_number = len(data["pages"])
    if part != []:
        total_number = len(part)

    for index in range(1, video_number+1):
        if not index in part and part != []:
            continue
        # 保存视频的文件夹为save_path\P+视频P数
        folder = os.path.join(save_path, f'P{index}')
        if not os.path.exists(folder):
            os.makedirs(folder)
        else:
            shutil.rmtree(folder)

        try:
            # 保存视频的文件夹在当前目录下
            print(
                f"Downloading P{index} ({total_number} in total)... \n")
            # 使用you-get进行下载
            print(
                fr'you-get https://www.bilibili.com/video/{bv}?p={index} -o {os.path.join(save_path, "P"+str(index))} --output-filename P{index} --no-caption >..\temp\output_{index}.txt')
            os.system(
                fr'you-get https://www.bilibili.com/video/{bv}?p={index} -o {os.path.join(save_path, "P"+str(index))} --output-filename P{index} --no-caption -d >..\temp\output_{index}.txt')
            # 如果os.system出错
            if os.path.getsize(os.path.join(os.path.pardir, 'temp', f'output_{index}.txt')) == 0:
                err_list.append(index)
                print(f"P{index} failed.\n")
                print(
                    '--------------------------------------------------------------------------------')
                continue
            print(f"P{index} finished.\n")
            print(f"Slicing video...\n")
            # 开一个新的进程，使用FFMPEG把视频拆成小视频，并生成M3U8文件
            os.system(
                fr'..\tools\ffmpeg\ffmpeg.exe -i "{os.path.join(save_path, "P"+str(index), "P"+str(index)+".flv")}" -c copy -map 0 -f segment -segment_list "{os.path.join(folder, "index.m3u8")}" -segment_time 30 "{os.path.join(folder, "P%03d.ts")}"')
            print(f"Slicing Done.\n")
            print(
                '--------------------------------------------------------------------------------')
        except:
            err_list.append(index)
            print(f"P{index} failed.\n")
            print(
                '--------------------------------------------------------------------------------')
            continue

    if err_list != [] and retry > 0:
        print(f"Failed to download {err_list}.\n")
        print('Retry...\n')
        download_video(bv, err_list, retry-1)

    elif err_list != [] and retry == 0:
        # 写一个错误日志
        with open('error.txt', 'w', encoding='utf-8') as f:
            # 把int转换成字符串
            # 读取下载失败的视频的日志
            err_log = '<hr>'
            for i in err_list:
                with open(os.path.join(os.path.pardir, 'temp', f'output_{i}.txt'), 'r', encoding='utf-8') as f2:
                    err_log += f'P{i}:\n' + f2.read()+"\n<hr>"
            err_list_str = ["P"+str(i) for i in err_list]
            f.write(ERR_LOG.format(
                bv=bv, err_list=", ".join(err_list_str), retry=RETRY,
                date=time.strftime("%Y-%m-%d %H:%M:%S", time.localtime()))
                + '\n\n\n'
                + str(data)
                + '\n\n\n'
                + err_log
            )
            f.close()
        print(f"Failed to download {err_list}.\n")
        print('Retry failed.\n')

    elif err_list == []:
        print(f"Download finished.\n")
        # 写一个完成日志
        with open('finished.txt', 'w', encoding='utf-8') as f:
            f.write(FINISHED_LOG.format(
                bv=bv, title=title, desc=desc, pubtime=pubtime, owner=owner['name'] +
                    f" ({owner['mid']})",
                    date=time.strftime("%Y-%m-%d %H:%M:%S", time.localtime())))
            f.close()

    # 读取并更新index.json文件
    with open(INDEX_PATH, 'r', encoding='utf-8') as f:
        indexJSON = json.load(f)
        f.close()
    # yyyy-mm-dd hh:mm:ss
    indexJSON["last_update"] = int(time.time())
    indexJSON["total"] += 1
    # 查找BV号是否已经存在
    # 如果存在，那么删去原来的数据
    for index, i in enumerate(indexJSON["data"]):
        if i["bv"] == bv:
            indexJSON["total"] -= 1
            del indexJSON["data"][index]
            break
    indexJSON["data"].append({
        "bv": bv,
        "title": title,
        "desc": desc,
        "pubtime": pubtime,
        "owner": owner,
        # 提取出来save_path最后一段的文件夹名字
        "path": os.path.split(save_path)[1],
        "update_time": int(time.time()),
    })
    # 更新index.json文件
    with open(INDEX_PATH, 'w', encoding='utf-8') as f:
        json.dump(indexJSON, f, ensure_ascii=False)
        f.close()

    part_old = []
    # 如果原来存在info.json文件，那么读取原来的数据
    if os.path.exists(os.path.join(save_path, 'info.json')):
        with open(os.path.join(save_path, 'info.json'), 'r', encoding='utf-8') as f:
            infoJSON = json.load(f)
            f.close()

        part_old = infoJSON["part_available"]
    # 合并part_old和parts，再从中减去err_list
    part_available = list(set(part_old+part))
    part_available = [i for i in part_available if i not in err_list]

    # 更新info.json文件
    with open(os.path.join(save_path, 'info.json'), 'w', encoding='utf-8') as f:
        json.dump({
            "bv": bv,
            "title": title,
            "desc": desc,
            "pubtime": pubtime,
            "owner": owner,
            "total_number": total_number,
            "part_available": part_available,
            # 分P信息
            "parts": parts,
        }, f, ensure_ascii=False)
        f.close()


if __name__ == "__main__":
    if len(sys.argv) == 1:
        print("Error: No BV number input.\n")
        sys.exit(0)
    elif len(sys.argv) == 2:
        bv = sys.argv[1]
        part = []
    elif len(sys.argv) == 3:
        bv = sys.argv[1]
        part = sys.argv[2].split(',')
        # 把字符串转换成int
        part = [int(i) for i in part]

    # 读取index.json文件
    with open(INDEX_PATH, 'r', encoding='utf-8') as f:
        index = json.load(f)
        f.close()

    # 遍历index.json文件，如果已经存在该视频，则把这个视频的Path 当做 save_path
    # index.json文件的格式为:
    # {
    #   "data": [
    #     {
    #       "bv": "BV1Z4411L7Zr",
    #       "title": "【李佳琦】《我不配》MV",
    #       "desc": "李佳琦《我不配》MV",
    #       "pubtime": 1600000000,
    #       "owner": {
    #         "mid": 123456,
    #         "name": "李佳琦",
    #         "save_path": "1600000000123456",
    #         "last_update": "125255266964522"
    #       }
    #     }
    #   ],
    #   "last_update": "125255266964522",
    #   "total": 1,
    #   "base_path": "data"
    # }

    for i in index["data"]:
        if i and i["bv"] == bv:
            print(
                "The video already exists in the database. \nTrying to update the video...\n")
            save_path = os.path.join(
                os.path.pardir, index['base_path'], i["path"])
            break
    download_video(bv, part=part, retry=RETRY)
