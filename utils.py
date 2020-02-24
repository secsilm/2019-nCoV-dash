import json
import logging
import subprocess
from collections import OrderedDict
from datetime import datetime
from pathlib import Path
import shutil

import matplotlib
matplotlib.use('Agg')
import geopandas
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import requests
from fake_useragent import UserAgent
from progressbar import progressbar

import config

logger = logging.getLogger(__name__)
ua = UserAgent()


def uniform_city_name(cn):
    if cn not in config.exceptions:
        cn = cn.rstrip("地区")
    cn = config.replace_map.get(cn, cn)
    return cn


def save_province_city_history():
    logger.info("[开始] 保存省市每日历史数据")
    try:
        headers = {"User-Agent": ua.random}
        r = requests.get("http://ncov.nosensor.com:8080/api/", headers=headers)
        r.raise_for_status()
        res = r.json()
        with open(
            f"history_data/province_city_history_{datetime.now().strftime('%Y%m%d')}.json",
            "w",
            encoding="utf-8",
        ) as f:
            json.dump(res, f, ensure_ascii=False, indent=4)
    except Exception as e:
        logger.error(f"保存省市每日历史数据出错。", exc_info=True)
    logger.info("[结束] 保存省市每日历史数据")


def save_dxy_minutes_history():
    logger.info("[开始] 保存丁香园每分钟历史数据")
    try:
        headers = {"User-Agent": ua.random}
        r = requests.get(
            "http://lab.isaaclin.cn/nCoV/api/area?latest=0", headers=headers
        )
        r.raise_for_status()
        res = r.json()
        with open(
            f"history_data/dxy_minutes_history_{datetime.now().strftime('%Y%m%d')}.json",
            "w",
            encoding="utf-8",
        ) as f:
            json.dump(res, f, ensure_ascii=False, indent=4)
    except Exception as e:
        logger.error(f"保存丁香园每分钟历史数据出错。", exc_info=True)
    logger.info("[结束] 保存丁香园每分钟历史数据")

def timestamp2datetime(ts):
    return datetime.fromtimestamp(ts)

def generate_figures(history, geomap, locations_list, start_date, end_date, dpi, figdir):
    # 哪个省在什么时间点的确诊、疑似、治愈、死亡人数
    # 省份，确诊，疑似，治愈，死亡，时间
    start_date = datetime.strptime(start_date, '%Y-%m-%d')
    end_date = datetime.strptime(f"{end_date} 23:59:59", '%Y-%m-%d %H:%M:%S')

    def plot_one_date(dt, geomap, times_dict, locations_list, filename):
        plot_data = []
        for p in locations_list:
            if p in times_dict[dt]:
                plot_data.append(times_dict[dt][p][0])
            else:
                plot_data.append(0)
        plot_series = pd.Series(plot_data, index=locations_list) + 1
        geomap.plot(plot_series.map(np.log), figsize=(5, 3))
        plt.axis("off")
        plt.text(93, 50, dt.replace('_', ' '), fontsize=10)
        plt.tight_layout()
        plt.savefig(f"{figdir}/{filename}.png", dpi=dpi)
        plt.close()

    short2full = {
        "广西": "广西壮族自治区",
        "内蒙古": "内蒙古自治区",
        "宁夏": "宁夏回族自治区",
        "新疆": "新疆维吾尔自治区",
        "西藏": "西藏自治区"
    }
    provinces, confirmeds, suspecteds, cureds, deads, times = [], [], [], [], [], []
    for r in history["results"]:
        time_ = timestamp2datetime(r["updateTime"] / 1000)
        if start_date <= time_ <= end_date:
            provinces.append(r["provinceShortName"])
            confirmeds.append(r["confirmedCount"])
            suspecteds.append(r["suspectedCount"])
            cureds.append(r["curedCount"])
            deads.append(r["deadCount"])
            times.append(time_)
    history_df = pd.DataFrame(
        data={
            "province": provinces,
            "confirmed": confirmeds,
            "suspected": suspecteds,
            "cured": cureds,
            "dead": deads,
            "time": times,
        }
    )
    history_df_sorted = history_df.sort_values(
        by="time", ascending=True, ignore_index=True
    )
    history_df_sorted.province = history_df_sorted.province.replace(short2full)

    # 生成 times_dict
    baseline = history_df_sorted.loc[0, "time"]
    max_interval = 0.5 * 3600  # 秒
    new_times = []
    times_dict = OrderedDict()
    for row in history_df_sorted.itertuples(index=False):
        if (row.time - baseline).seconds >= max_interval:
            baseline = row.time
        new_times.append(baseline)
        str_time = baseline.strftime("%Y-%m-%d_%H:%M:%S")
        if str_time not in times_dict:
            times_dict[str_time] = {}
        if row.province in times_dict[str_time]:
            if row.time > times_dict[str_time][row.province][-1]:
                times_dict[str_time][row.province] = [
                    row.confirmed,
                    row.suspected,
                    row.cured,
                    row.dead,
                    row.time,
                ]
        else:
            times_dict[str_time][row.province] = [
                row.confirmed,
                row.suspected,
                row.cured,
                row.dead,
                row.time,
            ]

    # last_time = "2020-01-22_03:28:10"
    last_time = list(times_dict.keys())[0]
    for k, v in times_dict.items():
        current_provinces_set = set(v.keys())
        last_provinces_set = set(times_dict[last_time].keys())
        diff = last_provinces_set - current_provinces_set
        if diff:
            times_dict[k].update(
                {province: times_dict[last_time][province] for province in diff}
            )
        last_time = k


    # 循环绘制多个 figures
    for i, k in progressbar(enumerate(times_dict)):
        plot_one_date(k, geomap, times_dict, locations_list, str(i))

def generate_video(image_pattern, videoname, fps):
    '''根据 image_pattern 指定的图片集生成名为 videoname 的视频，帧率由 fps 指定。'''
    cmd = f"ffmpeg -r {fps} -f image2 -s 1920x1080 -i {image_pattern} -vcodec libx264 -crf 25  -pix_fmt yuv420p {videoname}"
    logger.info(f"cmd={cmd}")
    subprocess.run(cmd)


def rmfigures(figdir):
    logger.info(f'正在删除 {figdir} 中的 PNG 文件 ...')
    count = 0
    for fname in Path(figdir).glob('*.png'):
        fname.unlink()
        count += 1
    logger.info(f"共删除 {count} 份 PNG 文件")