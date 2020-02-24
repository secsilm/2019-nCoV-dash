update_interval = 60 * 60 * 1000  # ms
# 网友自制的全国新型肺炎疫情实时数据接口：https://lab.isaaclin.cn/nCoV/
apis = {
    "qq": "https://service-n9zsbooc-1252957949.gz.apigw.tencentcs.com/release/qq",
    "dxy": "https://service-0gg71fu4-1252957949.gz.apigw.tencentcs.com/release/dingxiangyuan",
    "province_city_history": "http://ncov.nosensor.com:8080/api/",
    'qq_province': 'https://api.inews.qq.com/newsqa/v1/query/pubished/daily/list?province=省份名称',
    'qq_province_city': 'https://api.inews.qq.com/newsqa/v1/query/pubished/daily/list?province=省份名称&city=城市名称',
    'isaaclin_overall_latest': 'https://lab.isaaclin.cn/nCoV/api/overall?latest=1',
    'isaaclin_overall_history': 'https://lab.isaaclin.cn/nCoV/api/overall?latest=0',
    'isaaclin_area_latest': 'https://lab.isaaclin.cn/nCoV/api/area?latest=1',
    'isaaclin_area_history': 'https://lab.isaaclin.cn/nCoV/api/area?latest=0'
}
# You may not have to use mapboxtoken. It depends on what mapbox style you use.
# For more information, please see https://plot.ly/python/mapbox-layers/
# If you have to use it, you can create a file named .mapboxtoken and
# put your token in it.
with open(".mapboxtoken", "r") as f:
    token = f.read()

replace_map = {
    "乐东": "乐东黎族自治县",
    "伊犁州": "伊犁哈萨克自治州",
    "保亭": "保亭黎族苗族自治县",
    "六盘水": "六盘水市大湾镇",
    "凉山州": "凉山彝族自治州",
    "博尔塔拉": "博尔塔拉蒙古自治州",
    "巴音郭楞": "巴音郭楞蒙古自治州",
    "延边": "延边朝鲜族自治州",
    "恩施州": "恩施土家族苗族自治州",
    "昌吉州": "昌吉回族自治州",
    "昌江": "昌江黎族自治县",
    "海北州": "海北藏族自治州",
    "海南州": "海南藏族自治州",
    "湘西自治州": "湘西土家族苗族自治州",
    "玉树": "玉树藏族自治州",
    "琼中": "琼中黎族苗族自治县",
    "甘南": "甘南藏族自治州",
    "甘孜州": "甘孜藏族自治州",
    "阿坝州": "阿坝藏族羌族自治州",
    "陵水": "陵水黎族自治县",
    "黔东南州": "黔东南苗族侗族",
    "黔南州": "黔南布依族苗族",
    "黔西南州": "黔西南布依族苗族",
    "临夏": "临夏回族自治州",
    "临高": "临高县",
    "吐鲁番": "吐鲁番地区",
    "铜仁": "铜仁地区",
    "毕节": "毕节地区",
    "澄迈": "澄迈县",
    "巴州": "巴音郭楞蒙古自治州",
}

exceptions = []

# gunicorn config
workers = 1
# threads = 4
bind = "0.0.0.0:9102"
worker_class = "gevent"
worker_connections = 1500
timeout = 120
loglevel = "info"
accesslog = "log/gunicorn_access.log"
errorlog = "log/gunicorn_error.log"
daemon = True
pidfile = "gunicorn.pid"
