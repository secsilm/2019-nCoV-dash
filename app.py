"""
Main app.
"""

import concurrent.futures
import json
import logging
import logging.config
import time
from datetime import datetime
from pathlib import Path

import dash
import dash_core_components as dcc
import dash_daq as daq
import dash_html_components as html
import numpy as np
import pandas as pd
import plotly.graph_objs as go
import plotly.express as px
import requests
import yaml
from dash.dependencies import Input, Output
from fake_useragent import UserAgent
from plotly.subplots import make_subplots
import geopandas

import config
import utils

with open("logging_config.yml", "r", encoding="utf8") as f:
    logging_config = yaml.safe_load(f)
logging.config.dictConfig(logging_config)
logger = logging.getLogger(__name__)

app = dash.Dash(__name__)
server = app.server
colors = ["#E51017", "#FA893A", "#307D47", "#FFFFFF"]
virdis = [
    "#440154",
    "#443983",
    "#31688e",
    "#21918c",
    "#35b779",
    "#90d743",
    "#fde725",
]
plasma = ["#0d0887", "#5c01a6", "#9c179e", "#cc4778", "#ed7953", "#fdb42f", "#f0f921"]
inferno = ["#000004", "#320a5e", "#781c6d", "#bc3754", "#ed6925", "#fbb61a", "#fcffa4"]
cividis = ["#00224e", "#2a3f6d", "#575d6d", "#7d7c78", "#a59c74", "#d2c060", "#fee838"]
# colorscales = {
#     "confirmed": "Reds",
#     "suspected": "Oranges",
#     "cured": "Greens",
#     "dead": "gray_r",
# }
colorscales = {
    "确诊": inferno,
    "疑似": plasma,
    "治愈": virdis,
    "死亡": cividis,
}
executor = concurrent.futures.ThreadPoolExecutor(max_workers=5)

with open("data/china_provinces_v3.geojson") as f:
    provinces_map = json.load(f)
with open("data/china_cities_v2.geojson") as f:
    cities_map = json.load(f)
with open("data/description.md", "r", encoding="utf-8") as f:
    description = f.read()
provinces_geomap = geopandas.read_file("data/china_provinces_v3.geojson")
provinces_list = provinces_geomap.NL_NAME_1.values  # 地图中的省份
before24 = pd.DataFrame(
    data={
        "confirmed": [41, 41, 41, 45, 62, 198, 275, 291, 440, 571, 830],
        "suspected": [0, 0, 0, 0, 0, 0, 0, 54, 37, 393, 1072],
        "cured": [0, 0, 5, 8, 12, 17, 18, 25, 25, 25, 34],
        "dead": [1, 1, 2, 2, 2, 3, 4, 6, 9, 17, 25],
    },
    index=pd.date_range("2020-1-13", "2020-1-23"),
)
province_data_file = Path("history_data/province_data.csv")
city_data_file = Path("history_data/city_data.csv")

# 虽然直辖市为省级，但是此处仍将其纳入市级来展示
# 为了方便起见，台湾也计入其中
municipalities = ["北京", "上海", "天津", "重庆", "台湾", "香港"]

app.title = f"COVID-19 疫情趋势"
app.layout = html.Div(
    [
        html.H1(
            children=f"新型冠状病毒（2019-nCoV）肺炎（COVID-19）疫情趋势", style={"marginLeft": "3%"}
        ),
        html.Div(id="update-time-text", style={"marginLeft": "3%"}),
        dcc.Markdown(
            description,
            style={"marginLeft": "3%", "marginRight": "3%"},
            highlight_config={"theme": "dark"},
        ),
        html.Div(
            id="counts",
            style={
                "marginLeft": "5%",
                "marginRight": "5%",
                "marginBottom": "2%",
                "marginTop": "2%",
            },
            children=[
                html.Div(
                    style={
                        "width": "22%",
                        "display": "inline-block",
                        "marginRight": ".8%",
                    },
                    children=[
                        daq.LEDDisplay(
                            id="confirmed-count",
                            label="确诊总计",
                            color=colors[0],
                            size=40,
                            labelPosition="bottom",
                            theme={"dark": True},
                            backgroundColor="black",
                        )
                    ],
                ),
                html.Div(
                    style={
                        "width": "22%",
                        "display": "inline-block",
                        "marginRight": ".8%",
                    },
                    children=[
                        daq.LEDDisplay(
                            id="suspected-count",
                            label="疑似总计",
                            color=colors[1],
                            size=40,
                            labelPosition="bottom",
                            backgroundColor="black",
                        )
                    ],
                ),
                html.Div(
                    style={
                        "width": "22%",
                        "display": "inline-block",
                        "marginRight": ".8%",
                    },
                    children=[
                        daq.LEDDisplay(
                            id="cured-count",
                            label="治愈总计",
                            color=colors[2],
                            size=40,
                            labelPosition="bottom",
                            backgroundColor="black",
                        )
                    ],
                ),
                html.Div(
                    style={
                        "width": "22%",
                        "display": "inline-block",
                        "marginRight": ".8%",
                    },
                    children=[
                        daq.LEDDisplay(
                            id="dead-count",
                            label="死亡总计",
                            color=colors[3],
                            size=40,
                            labelPosition="bottom",
                            backgroundColor="black",
                        )
                    ],
                ),
            ],
        ),
        dcc.Interval(
            id="interval-component", interval=config.update_interval, n_intervals=0
        ),
        dcc.Loading(
            id="loading-trend",
            children=[
                dcc.Graph(
                    id="trend",
                    style={
                        "width": "90%",
                        "marginRight": "3%",
                        "marginLeft": "3%",
                        "marginTop": "2%",
                        "marginBottom": "2%",
                    },
                ),
            ],
            # 'graph', 'cube', 'circle', 'dot', or 'default'
            type="graph",
        ),
        html.Div(
            [
                html.H2("省级地图"),
                html.Span(
                    dcc.RadioItems(
                        id="province-radio",
                        options=[
                            {"label": "确诊", "value": "确诊"},
                            {"label": "疑似", "value": "疑似"},
                            {"label": "治愈", "value": "治愈"},
                            {"label": "死亡", "value": "死亡"},
                        ],
                        value="确诊",
                        labelStyle={"display": "inline-block"},
                    ),
                ),
            ],
            style={"marginLeft": "3%", "display": "inline-block"},
        ),
        dcc.Loading(
            id="loading-province-map",
            children=[
                dcc.Graph(
                    id="province-level-map",
                    style={
                        "height": "600px",
                        "width": "90%",
                        "marginRight": "5%",
                        "marginLeft": "5%",
                        "marginTop": "2%",
                        "marginBottom": "2%",
                    },
                ),
            ],
            type="cube",
        ),
        html.Div(
            [
                html.H2("市级地图"),
                html.Span(
                    dcc.RadioItems(
                        id="city-radio",
                        options=[
                            {"label": "确诊", "value": "确诊"},
                            {"label": "疑似", "value": "疑似"},
                            {"label": "治愈", "value": "治愈"},
                            {"label": "死亡", "value": "死亡"},
                        ],
                        value="确诊",
                        labelStyle={"display": "inline-block"},
                    ),
                ),
            ],
            style={"marginLeft": "3%", "display": "inline-block"},
        ),
        dcc.Loading(
            id="loading-city-map",
            children=[
                dcc.Graph(
                    id="city-level-map",
                    style={
                        "height": "600px",
                        "width": "90%",
                        "marginRight": "5%",
                        "marginLeft": "5%",
                        "marginTop": "2%",
                        "marginBottom": "2%",
                    },
                ),
            ],
            type="cube",
        ),
        html.Div(
            [
                html.H2("生成省级疫情动态变化图"),
                html.P("请先在下方选择开始和结束日期，闭区间："),
                dcc.DatePickerRange(
                    id="date-range",
                    min_date_allowed=datetime(2020, 1, 22),
                    # max_date_allowed=datetime(2020, 2, 14),
                    start_date_placeholder_text="请选择开始日期",
                    end_date_placeholder_text="请选择结束日期",
                    display_format="YYYY-MM-DD",
                    month_format="YYYY-MM",
                ),
                html.Button(
                    "确定",
                    id="submit",
                    style={"width": "80px", "height": "43px", "marginLeft": "2%"},
                ),
                dcc.Loading(
                    children=[
                        html.Video(
                            id="video",
                            controls=True,
                            style={
                                "width": "90%",
                                "marginLeft": "2%",
                                "marginRight": "5%",
                                "marginTop": "2%",
                                "marginBottom": "2%",
                            },
                        ),
                    ]
                ),
            ],
            style={"marginLeft": "3%"},
        ),
    ],
)


def generate_province_city_datafile():
    """生成省级和市级数据文件，这些文件用于绘制地图。"""
    headers = {"User-Agent": utils.ua.random}
    r = requests.get(config.apis["isaaclin_area_latest"], headers=headers)
    r.raise_for_status()
    res = r.json()
    province, confirmed, suspected, cured, dead = zip(
        *[
            (
                i["provinceName"].rstrip("省").rstrip("市"),
                i["confirmedCount"],
                i["suspectedCount"],
                i["curedCount"],
                i["deadCount"],
            )
            for i in res["results"]
            if i["countryName"] == "中国"
        ]
    )
    df = pd.DataFrame(
        data={
            "地区": province,
            "确诊": confirmed,
            "疑似": suspected,
            "治愈": cured,
            "死亡": dead,
        },
    )
    df.to_csv(province_data_file, encoding="utf8")

    cities, confirmeds, suspecteds, cureds, deads = [], [], [], [], []
    for province in res["results"]:
        if province["countryName"] != "中国":
            continue
        if province["provinceShortName"] in municipalities:
            cities.append(province["provinceShortName"])
            confirmeds.append(province["confirmedCount"])
            suspecteds.append(province["suspectedCount"])
            cureds.append(province["curedCount"])
            deads.append(province["deadCount"])
            continue
        for city in province["cities"]:
            cities.append(city["cityName"])
            confirmeds.append(city["confirmedCount"])
            suspecteds.append(city["suspectedCount"])
            cureds.append(city["curedCount"])
            deads.append(city["deadCount"])
    cities = [utils.uniform_city_name(cn) for cn in cities]
    df = pd.DataFrame(
        data={
            "地区": cities,
            "确诊": confirmeds,
            "疑似": suspecteds,
            "治愈": cureds,
            "死亡": deads,
        },
    )
    df.to_csv(city_data_file, encoding="utf8")


@app.callback(
    [
        Output("trend", "figure"),
        Output("update-time-text", "children"),
        Output("confirmed-count", "value"),
        Output("suspected-count", "value"),
        Output("cured-count", "value"),
        Output("dead-count", "value"),
    ],
    [Input("interval-component", "n_intervals")],
)
def update_graph_and_counts(n):
    """更新面积图、折线图和当前确诊、疑似、治愈和死亡人数。"""

    # future1 = executor.submit(utils.save_province_city_history)
    # future2 = executor.submit(utils.save_dxy_minutes_history)

    headers = {"User-Agent": utils.ua.random}
    r = requests.get(config.apis["isaaclin_overall_history"], headers=headers)
    r.raise_for_status()
    res = r.json()
    with open(
        f"history_data/isaaclin_overall_{datetime.now().strftime('%Y%m%d')}.json",
        "w",
        encoding="utf-8",
    ) as f:
        json.dump(res, f, ensure_ascii=False, indent=4)
    time_, confirmed, suspected, cured, dead = zip(
        *[
            (
                i["updateTime"],
                i["confirmedCount"],
                i["suspectedCount"],
                i["curedCount"],
                i["deadCount"],
            )
            for i in res["results"]
        ]
    )
    time_ = [utils.timestamp2datetime(t / 1000) for t in time_]
    latest_update_time = time_[0]
    latest_confirmed = confirmed[0]
    latest_suspected = suspected[0]
    latest_cured = cured[0]
    latest_dead = dead[0]
    df = pd.DataFrame(
        data={
            "time": time_,
            "confirmed": confirmed,
            "suspected": suspected,
            "cured": cured,
            "dead": dead,
        }
    )
    df = df.resample("D", on="time")
    df = df.apply(lambda series: series.sort_values(ignore_index=True).iloc[-1])
    df = df.drop(columns="time")
    df = pd.concat([before24, df])

    new_from_yesterday = df.diff(periods=1)

    fig = make_subplots(
        rows=3,
        cols=1,
        shared_xaxes=True,
        subplot_titles=["确诊疑似人数堆积面积图", "治愈死亡人数折线图", "较昨日新增确诊、疑似、治愈和死亡人数折线图"],
    )
    trace_confirmed = go.Scatter(
        x=df.index,
        y=df.confirmed,
        marker=dict(color=colors[0]),
        mode="lines+markers",
        hovertemplate="确诊：%{y}<extra></extra>",
        name="确诊",
        stackgroup="one",
    )
    trace_suspected = go.Scatter(
        x=df.index,
        y=df.suspected,
        marker=dict(color=colors[1]),
        mode="lines+markers",
        hovertemplate="疑似：%{y}<extra></extra>",
        name="疑似",
        stackgroup="one",
    )
    trace_cured = go.Scatter(
        x=df.index,
        y=df.cured,
        marker=dict(color=colors[2]),
        mode="lines+markers",
        hovertemplate="治愈：%{y}<extra></extra>",
        name="治愈",
    )
    trace_dead = go.Scatter(
        x=df.index,
        y=df.dead,
        marker=dict(color=colors[3]),
        mode="lines+markers",
        hovertemplate="死亡：%{y}<extra></extra>",
        name="死亡",
    )
    trace_confirmed_new = go.Scatter(
        x=df.index,
        y=new_from_yesterday["confirmed"],
        marker=dict(color=colors[0]),
        mode="lines+markers",
        hovertemplate="新增确诊：%{y}<extra></extra>",
        name="较昨日新增确诊",
    )
    trace_suspected_new = go.Scatter(
        x=df.index,
        y=new_from_yesterday["suspected"],
        marker=dict(color=colors[1]),
        mode="lines+markers",
        hovertemplate="新增疑似：%{y}<extra></extra>",
        name="较昨日新增疑似",
    )
    trace_cured_new = go.Scatter(
        x=df.index,
        y=new_from_yesterday["cured"],
        marker=dict(color=colors[2]),
        mode="lines+markers",
        hovertemplate="新增治愈：%{y}<extra></extra>",
        name="较昨日新增治愈",
    )
    trace_dead_new = go.Scatter(
        x=df.index,
        y=new_from_yesterday["dead"],
        marker=dict(color=colors[3]),
        mode="lines+markers",
        hovertemplate="新增死亡：%{y}<extra></extra>",
        name="较昨日新增死亡",
    )

    fig.append_trace(trace_confirmed, 1, 1)
    fig.append_trace(trace_suspected, 1, 1)
    fig.append_trace(trace_dead, 2, 1)
    fig.append_trace(trace_cured, 2, 1)
    fig.append_trace(trace_confirmed_new, 3, 1)
    fig.append_trace(trace_suspected_new, 3, 1)
    fig.append_trace(trace_cured_new, 3, 1)
    fig.append_trace(trace_dead_new, 3, 1)
    margin = go.layout.Margin(l=100, r=100, b=50, t=25, pad=4)
    fig["layout"].update(margin=margin, showlegend=True, template="plotly_dark")
    return (
        fig,
        f'网页更新时间：{datetime.now().strftime("%Y-%m-%d %H:%M:%S")}，每 {config.update_interval // 60000} 分钟更新一次。数据实际更新时间：{latest_update_time.strftime("%Y-%m-%d %H:%M:%S")}',
        f"{latest_confirmed:05d}",
        f"{latest_suspected:05d}",
        f"{latest_cured:05d}",
        f"{latest_dead:05d}",
    )


@app.callback(
    Output("province-level-map", "figure"),
    [Input("interval-component", "n_intervals"), Input("province-radio", "value")],
)
def update_province_map(n, selected_radio):
    """更新省级地图。"""
    if (
        not province_data_file.exists()
        or (
            datetime.now() - datetime.fromtimestamp(province_data_file.stat().st_mtime)
        ).seconds
        > 3600
    ):
        time.sleep(3)
        generate_province_city_datafile()

    df = pd.read_csv(province_data_file, index_col=0)
    # df = df.applymap(np.log)
    labels = ["0", "1-9", "10-99", "100-499", "500-999", "1000-9999", "10000+"]
    # bins 是左闭右开
    df["确诊区间"] = pd.cut(
        df["确诊"],
        bins=[0, 1, 10, 100, 500, 1000, 10000, 100000],
        precision=0,
        right=False,
        labels=labels,
    )
    df["疑似区间"] = pd.cut(
        df["疑似"],
        bins=[0, 1, 10, 100, 500, 1000, 10000, 100000],
        precision=0,
        right=False,
        labels=labels,
    )
    df["治愈区间"] = pd.cut(
        df["治愈"],
        bins=[0, 1, 10, 100, 500, 1000, 10000, 100000],
        precision=0,
        right=False,
        labels=labels,
    )
    df["死亡区间"] = pd.cut(
        df["死亡"],
        bins=[0, 1, 10, 100, 500, 1000, 10000, 100000],
        precision=0,
        right=False,
        labels=labels,
    )
    fig = px.choropleth_mapbox(
        df,
        geojson=provinces_map,
        color=f"{selected_radio}区间",
        locations="地区",
        featureidkey="properties.NL_NAME_1",
        mapbox_style="carto-darkmatter",
        color_discrete_map={
            "0": colorscales[selected_radio][0],
            "1-9": colorscales[selected_radio][1],
            "10-99": colorscales[selected_radio][2],
            "100-499": colorscales[selected_radio][3],
            "500-999": colorscales[selected_radio][4],
            "1000-9999": colorscales[selected_radio][5],
            "10000+": colorscales[selected_radio][6],
        },
        category_orders={f"{selected_radio}区间": labels},
        center={"lat": 35.110573, "lon": 106.493924},
        zoom=3,
        hover_name="地区",
        hover_data=["确诊", "疑似", "治愈", "死亡"],
    )
    fig.update_layout(margin={"r": 0, "t": 0, "l": 0, "b": 0})
    return fig


@app.callback(
    Output("city-level-map", "figure"),
    [Input("interval-component", "n_intervals"), Input("city-radio", "value")],
)
def update_city_map(n, selected_radio):
    """更新市级地图。"""
    while (
        not city_data_file.exists()
        or (
            datetime.now() - datetime.fromtimestamp(city_data_file.stat().st_mtime)
        ).seconds
        > 3600
    ):
        time.sleep(2)
    df = pd.read_csv(city_data_file)
    # df = df.applymap(np.log)
    labels = ["0", "1-9", "10-99", "100-499", "500-999", "1000-9999", "10000+"]
    # bins 是左闭右开
    df["确诊区间"] = pd.cut(
        df["确诊"],
        bins=[0, 1, 10, 100, 500, 1000, 10000, 100000],
        precision=0,
        right=False,
        labels=labels,
    )
    df["疑似区间"] = pd.cut(
        df["疑似"],
        bins=[0, 1, 10, 100, 500, 1000, 10000, 100000],
        precision=0,
        right=False,
        labels=labels,
    )
    df["治愈区间"] = pd.cut(
        df["治愈"],
        bins=[0, 1, 10, 100, 500, 1000, 10000, 100000],
        precision=0,
        right=False,
        labels=labels,
    )
    df["死亡区间"] = pd.cut(
        df["死亡"],
        bins=[0, 1, 10, 100, 500, 1000, 10000, 100000],
        precision=0,
        right=False,
        labels=labels,
    )
    fig = px.choropleth_mapbox(
        df,
        geojson=cities_map,
        color=f"{selected_radio}区间",
        locations="地区",
        featureidkey="properties.NAME",
        mapbox_style="carto-darkmatter",
        color_discrete_map={
            "0": colorscales[selected_radio][0],
            "1-9": colorscales[selected_radio][1],
            "10-99": colorscales[selected_radio][2],
            "100-499": colorscales[selected_radio][3],
            "500-999": colorscales[selected_radio][4],
            "1000-9999": colorscales[selected_radio][5],
            "10000+": colorscales[selected_radio][6],
        },
        # color_discrete_sequence='plasma',
        category_orders={f"{selected_radio}区间": labels},
        center={"lat": 35.110573, "lon": 106.493924},
        zoom=3,
        hover_name="地区",
        hover_data=["确诊", "疑似", "治愈", "死亡"],
    )
    fig.update_layout(margin={"r": 0, "t": 0, "l": 0, "b": 0})
    return fig


@app.callback(
    Output("video", "src"),
    [
        Input("date-range", "start_date"),
        Input("date-range", "end_date"),
        Input("submit", "n_clicks_timestamp"),
    ],
)
def update_video(start_date, end_date, n_clicks_timestamp):
    logger.info(f"n_clicks_timestamp={n_clicks_timestamp}")
    latest_file = max(
        Path("history_data/").glob("dxy_minutes*.json"), key=lambda p: p.stat().st_ctime
    )
    with open(latest_file, "r", encoding="utf8",) as f:
        history = json.load(f)
    if (
        start_date
        and end_date
        and n_clicks_timestamp
        and (n_clicks_timestamp != -1)
        and (
            datetime.now() - utils.timestamp2datetime(n_clicks_timestamp / 1000)
        ).seconds
        < 1
    ):
        logger.info("[开始] 更新视频")
        fps = 30
        dpi = 300
        figdir = "assets/figures"
        Path(figdir).mkdir(exist_ok=True, parents=True)
        utils.rmfigures(figdir)
        logger.info("[开始] 生成图片")
        utils.generate_figures(
            history, provinces_geomap, provinces_list, start_date, end_date, dpi, figdir
        )
        logger.info("[结束] 生成图片")
        videoname = f"assets/tncg-{start_date.replace('-', '')}-{end_date.replace('-', '')}-{datetime.now().strftime('%Y%m%d%H%M%S')}.mp4"
        logger.info("[开始] 生成视频")
        utils.generate_video(f"{figdir}/%d.png", videoname, 30)
        logger.info("[结束] 生成视频")
        logger.info("[结束] 更新视频")
        src = f"/{videoname}"
        logger.debug(f"src={src}")
        return src


if __name__ == "__main__":
    app.run_server(host="0.0.0.0", port=9102, debug=False)
