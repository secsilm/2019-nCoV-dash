"""
Dash app.
"""

import json
from datetime import datetime
import time

import dash
import dash_core_components as dcc
import dash_daq as daq
import dash_html_components as html
import numpy as np
import pandas as pd
import plotly.graph_objs as go
import requests
from dash.dependencies import Input, Output
from plotly.subplots import make_subplots
from fake_useragent import UserAgent

import config

app = dash.Dash(__name__)
colors = ["#E51017", "#FA893A", "#307D47", "#FFFFFF"]
colorscales = {
    "confirmeds": "Reds",
    "suspecteds": "Oranges",
    "cureds": "Greens",
    "deads": "gray_r",
}

ua = UserAgent()

with open("data/china_provinces_v2.geojson") as f:
    provinces_map = json.load(f)
with open("data/china_cities_github.geojson") as f:
    cities_map = json.load(f)
with open("data/description.md", "r", encoding="utf-8") as f:
    description = f.read()

# 虽然直辖市为省级，但是此处仍将其纳入市级来展示
# 为了方便起见，台湾也计入其中
municipalities = ["北京", "上海", "天津", "重庆", "台湾", "香港"]


def uniform_city_name(cn):
    if cn not in config.exceptions:
        cn = cn.rstrip("地区")
    cn = config.replace_map.get(cn, cn)
    return cn


app.title = f"新型冠状病毒 2019-nCoV 疫情趋势"
app.layout = html.Div(
    [
        html.H1(children=f"新型冠状病毒 2019-nCoV 疫情趋势", style={"marginLeft": "3%"}),
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
                            {"label": "确诊", "value": "confirmeds"},
                            {"label": "疑似", "value": "suspecteds"},
                            {"label": "治愈", "value": "cureds"},
                            {"label": "死亡", "value": "deads"},
                        ],
                        value="confirmeds",
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
                            {"label": "确诊", "value": "confirmeds"},
                            {"label": "疑似", "value": "suspecteds"},
                            {"label": "治愈", "value": "cureds"},
                            {"label": "死亡", "value": "deads"},
                        ],
                        value="confirmeds",
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
    ],
)


@app.callback(Output("trend", "figure"), [Input("interval-component", "n_intervals")])
def update_graph(n):
    start_update = time.time()
    headers = {"User-Agent": ua.random}
    start = time.time()
    r = requests.get(config.apis["qq"], headers=headers)
    print(f"请求 qq 接口耗时={time.time() - start} s")
    r.raise_for_status()
    res = r.json()
    data = res["data"]["wuwei_ww_cn_day_counts"]
    dates, confirmeds, suspecteds, deads, cureds = zip(
        *[(i["date"], i["confirm"], i["suspect"], i["dead"], i["heal"]) for i in data]
    )
    dates = [f"2020-{'-'.join(i.split('/'))}" for i in dates]
    dates, confirmeds, suspecteds, deads, cureds = zip(
        *sorted(zip(dates, confirmeds, suspecteds, deads, cureds))
    )

    new_from_yesterday = pd.DataFrame(
        data={
            "confirmeds": confirmeds,
            "suspecteds": suspecteds,
            "cureds": cureds,
            "deads": deads,
        },
        index=dates,
        dtype=int,
    ).diff(periods=1)

    fig = make_subplots(
        rows=3,
        cols=1,
        shared_xaxes=True,
        subplot_titles=["确诊疑似人数堆积面积图", "治愈死亡人数折线图", "较昨日新增确诊、疑似、治愈和死亡人数折线图"],
    )
    trace_confirmed = go.Scatter(
        x=dates,
        y=confirmeds,
        marker=dict(color=colors[0]),
        mode="lines+markers",
        hovertemplate="确诊：%{y}<extra></extra>",
        name="确诊",
        stackgroup="one",
    )
    trace_suspected = go.Scatter(
        x=dates,
        y=suspecteds,
        marker=dict(color=colors[1]),
        mode="lines+markers",
        hovertemplate="疑似：%{y}<extra></extra>",
        name="疑似",
        stackgroup="one",
    )
    trace_cured = go.Scatter(
        x=dates,
        y=cureds,
        marker=dict(color=colors[2]),
        mode="lines+markers",
        hovertemplate="治愈：%{y}<extra></extra>",
        name="治愈",
    )
    trace_dead = go.Scatter(
        x=dates,
        y=deads,
        marker=dict(color=colors[3]),
        mode="lines+markers",
        hovertemplate="死亡：%{y}<extra></extra>",
        name="死亡",
    )
    trace_confirmed_new = go.Scatter(
        x=dates,
        y=new_from_yesterday["confirmeds"],
        marker=dict(color=colors[0]),
        mode="lines+markers",
        hovertemplate="新增确诊：%{y}<extra></extra>",
        name="较昨日新增确诊",
    )
    trace_suspected_new = go.Scatter(
        x=dates,
        y=new_from_yesterday["suspecteds"],
        marker=dict(color=colors[1]),
        mode="lines+markers",
        hovertemplate="新增疑似：%{y}<extra></extra>",
        name="较昨日新增疑似",
    )
    trace_cured_new = go.Scatter(
        x=dates,
        y=new_from_yesterday["cureds"],
        marker=dict(color=colors[2]),
        mode="lines+markers",
        hovertemplate="新增治愈：%{y}<extra></extra>",
        name="较昨日新增治愈",
    )
    trace_dead_new = go.Scatter(
        x=dates,
        y=new_from_yesterday["deads"],
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
    print(f"更新 trend 耗时={time.time() - start_update} s")
    return fig


@app.callback(
    [
        Output("update-time-text", "children"),
        Output("confirmed-count", "value"),
        Output("suspected-count", "value"),
        Output("dead-count", "value"),
        Output("cured-count", "value"),
    ],
    [Input("interval-component", "n_intervals")],
)
def update_counts(n):
    headers = {"User-Agent": ua.random}
    r = requests.get(config.apis["qq"], headers=headers)
    r.raise_for_status()
    res = r.json()
    with open(
        f"data/qq_{datetime.now().strftime('%Y%m%d')}.json", "w", encoding="utf-8",
    ) as f:
        json.dump(res, f, ensure_ascii=False, indent=4)
    confirmed = res["data"]["wuwei_ww_global_vars"][0]["confirmCount"]
    suspected = res["data"]["wuwei_ww_global_vars"][0]["suspectCount"]
    dead = res["data"]["wuwei_ww_global_vars"][0]["deadCount"]
    cured = res["data"]["wuwei_ww_global_vars"][0]["cure"]
    update_time = res["data"]["wuwei_ww_global_vars"][0]["update_time"]

    # 省市每日历史数据
    try:
        r = requests.get("http://ncov.nosensor.com:8080/api/", headers=headers)
        r.raise_for_status()
        res = r.json()
        with open(
            f"data/province_city_history_{datetime.now().strftime('%Y%m%d')}.json",
            "w",
            encoding="utf-8",
        ) as f:
            json.dump(res, f, ensure_ascii=False, indent=4)
    except Exception as e:
        print(f"保存省市每日历史数据出错。{e}")
    # 丁香园每分钟历史数据
    try:
        r = requests.get(
            "http://lab.isaaclin.cn/nCoV/api/area?latest=0", headers=headers
        )
        r.raise_for_status()
        res = r.json()
        with open(
            f"data/dxy_minutes_history_{datetime.now().strftime('%Y%m%d')}.json",
            "w",
            encoding="utf-8",
        ) as f:
            json.dump(res, f, ensure_ascii=False, indent=4)
    except Exception as e:
        print(f"保存丁香园每分钟历史数据出错。{e}")

    return (
        f'更新时间：{datetime.now().strftime("%Y-%m-%d %H:%M:%S")}，每 {config.update_interval // 60000} 分钟更新一次。',
        f"{confirmed:05d}",
        f"{suspected:05d}",
        f"{dead:05d}",
        f"{cured:05d}",
    )


@app.callback(
    Output("province-level-map", "figure"),
    [Input("interval-component", "n_intervals"), Input("province-radio", "value")],
)
def update_province_map(n, selected_radio):
    start_update = time.time()
    headers = {"User-Agent": ua.random}
    start = time.time()
    r = requests.get(config.apis["dxy"], headers=headers)
    print(f"请求丁香园接口耗时={time.time() - start}s")
    r.raise_for_status()
    res = r.json()
    data = res["data"]["getAreaStat"]
    provinces, confirmeds, suspecteds, cureds, deads = zip(
        *[
            (
                i["provinceName"].rstrip("省").rstrip("市"),
                i["confirmedCount"],
                i["suspectedCount"],
                i["curedCount"],
                i["deadCount"],
            )
            for i in data
        ]
    )
    df = pd.DataFrame(
        data={
            "confirmeds": confirmeds,
            "suspecteds": suspecteds,
            "cureds": cureds,
            "deads": deads,
        },
        columns=["confirmeds", "suspecteds", "cureds", "deads"],
        index=provinces,
    )
    df.to_csv("data/provinces_data.csv", index=True, encoding="utf8")
    df = df.applymap(np.log)
    # confirmeds_log = np.log(np.add(confirmeds, 1))
    fig = go.Figure(
        go.Choroplethmapbox(
            featureidkey="properties.NL_NAME_1",
            geojson=provinces_map,
            locations=provinces,
            z=df[selected_radio],
            zauto=True,
            colorscale=colorscales[selected_radio],
            reversescale=True,
            marker_opacity=0.8,
            marker_line_width=0.8,
            customdata=np.vstack((provinces, confirmeds, suspecteds, cureds, deads)).T,
            hovertemplate="<b>%{customdata[0]}</b><br><br>"
            + "确诊：%{customdata[1]}<br>"
            + "疑似：%{customdata[2]}<br>"
            + "治愈：%{customdata[3]}<br>"
            + "死亡：%{customdata[4]}<br>"
            + "<extra></extra>",
            showscale=False,
        )
    )
    fig.update_layout(
        mapbox_style="carto-darkmatter",
        mapbox_zoom=3,
        mapbox_center={"lat": 35.110573, "lon": 106.493924},
        mapbox_accesstoken=config.token,
    )
    fig.update_layout(margin={"r": 0, "t": 0, "l": 0, "b": 0})
    print(f"更新省级地图耗时={time.time() - start_update} s")
    return fig


@app.callback(
    Output("city-level-map", "figure"),
    [Input("interval-component", "n_intervals"), Input("city-radio", "value")],
)
def update_city_map(n, selected_radio):
    start_update = time.time()
    headers = {"User-Agent": ua.random}
    start = time.time()
    r = requests.get(config.apis["dxy"], headers=headers)
    print(f"请求丁香园接口耗时={time.time() - start} s")
    r.raise_for_status()
    res = r.json()
    with open(
        f"data/dxy_{datetime.now().strftime('%Y%m%d')}.json", "w", encoding="utf-8",
    ) as f:
        json.dump(res, f, ensure_ascii=False, indent=4)
    data = res["data"]["getAreaStat"]
    cities, confirmeds, suspecteds, cureds, deads = [], [], [], [], []
    for province in data:
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
    cities = [uniform_city_name(cn) for cn in cities]
    confirmeds_log = np.log(np.add(confirmeds, 1))
    df = pd.DataFrame(
        data={
            "confirmeds": confirmeds,
            "suspecteds": suspecteds,
            "cureds": cureds,
            "deads": deads,
        },
        index=cities,
    )
    df.to_csv("data/cities_data.csv", index=True, encoding="utf8")
    df = df.applymap(np.log)
    fig = go.Figure(
        go.Choroplethmapbox(
            featureidkey="properties.NAME",
            geojson=cities_map,
            locations=cities,
            z=df[selected_radio],
            zauto=True,
            colorscale=colorscales[selected_radio],
            reversescale=True,
            marker_opacity=0.8,
            marker_line_width=0.8,
            customdata=np.vstack((cities, confirmeds, suspecteds, cureds, deads)).T,
            hovertemplate="<b>%{customdata[0]}</b><br><br>"
            + "确诊：%{customdata[1]}<br>"
            + "疑似：%{customdata[2]}<br>"
            + "治愈：%{customdata[3]}<br>"
            + "死亡：%{customdata[4]}<br>"
            + "<extra></extra>",
            showscale=False,
        )
    )
    fig.update_layout(
        mapbox_style="carto-darkmatter",
        mapbox_zoom=3,
        mapbox_center={"lat": 35.110573, "lon": 106.493924},
        mapbox_accesstoken=config.token,
    )
    fig.update_layout(margin={"r": 0, "t": 0, "l": 0, "b": 0})
    print(f"更新市级地图耗时={time.time() - start_update} s")
    return fig


if __name__ == "__main__":
    app.run_server(host="0.0.0.0", port=9102, debug=False)
