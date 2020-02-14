import logging
from datetime import datetime
import requests
from fake_useragent import UserAgent
import config
import json

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
