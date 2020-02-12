"""
Dash app.
"""

import json
from datetime import datetime

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

ua = UserAgent()

with open("data/china_provinces_v2.geojson") as f:
    provinces_map = json.load(f)
with open("data/china_cities_github.geojson") as f:
    cities_map = json.load(f)
with open("data/description.md", "r", encoding="utf-8") as f:
    description = f.read()

# print(f"香港 in provinces_map={'香港' in provinces_map.NL_NAME_1.values}")
# print(f"香港 in cities_map={'香港' in cities_map.NAME.values}")

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
            description, style={"marginLeft": "3%", "marginRight": "3%"}, highlight_config={"theme": "dark"}
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
                        # "backgroundColor": "#cbd2d3",
                        "display": "inline-block",
                        "marginRight": ".8%",
                    },
                    children=[
                        daq.LEDDisplay(
                            id="confirmed-count",
                            label="确诊总计",
                            color=colors[0],
                            size=50,
                            labelPosition="bottom",
                            theme={'dark': True},
                            backgroundColor='black'
                        )
                    ],
                ),
                html.Div(
                    style={
                        "width": "22%",
                        # "backgroundColor": "#cbd2d3",
                        "display": "inline-block",
                        "marginRight": ".8%",
                    },
                    children=[
                        daq.LEDDisplay(
                            id="suspected-count",
                            label="疑似总计",
                            color=colors[1],
                            size=50,
                            labelPosition="bottom",
                            backgroundColor='black'
                        )
                    ],
                ),
                html.Div(
                    style={
                        "width": "22%",
                        # "backgroundColor": "#cbd2d3",
                        "display": "inline-block",
                        "marginRight": ".8%",
                    },
                    children=[
                        daq.LEDDisplay(
                            id="cured-count",
                            label="治愈总计",
                            color=colors[2],
                            size=50,
                            labelPosition="bottom",
                            backgroundColor='black'
                        )
                    ],
                ),
                html.Div(
                    style={
                        "width": "22%",
                        # "backgroundColor": "#cbd2d3",
                        "display": "inline-block",
                        "marginRight": ".8%",
                    },
                    children=[
                        daq.LEDDisplay(
                            id="dead-count",
                            label="死亡总计",
                            color=colors[3],
                            size=50,
                            labelPosition="bottom",
                            backgroundColor='black'
                        )
                    ],
                ),
            ],
        ),
        dcc.Interval(
            id="interval-component", interval=config.update_interval, n_intervals=0
        ),
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
)


@app.callback(Output("trend", "figure"), [Input("interval-component", "n_intervals")])
def update_graph(n):
    headers = {"User-Agent": ua.random}
    r = requests.get(config.apis["qq"], headers=headers)
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

    fig = make_subplots(rows=2, cols=1, shared_xaxes=True)
    trace_confirmed = go.Scatter(
        x=dates,
        y=confirmeds,
        marker=dict(color=colors[0]),
        mode="lines+markers",
        hovertemplate="确诊：%{y}<extra></extra>",
        name="确诊",
    )
    trace_suspected = go.Scatter(
        x=dates,
        y=suspecteds,
        marker=dict(color=colors[1]),
        mode="lines+markers",
        hovertemplate="疑似：%{y}<extra></extra>",
        name="疑似",
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

    fig.append_trace(trace_confirmed, 1, 1)
    fig.append_trace(trace_suspected, 1, 1)
    fig.append_trace(trace_dead, 2, 1)
    fig.append_trace(trace_cured, 2, 1)
    margin = go.layout.Margin(l=100, r=100, b=50, t=25, pad=4)
    fig["layout"].update(margin=margin, showlegend=True, template="plotly_dark")
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
        f"data/qq_{datetime.now().strftime('%Y%m%d')}.json",
        "w",
        encoding="utf-8",
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
    Output("province-level-map", "figure"), [Input("interval-component", "n_intervals")]
)
def update_province_map(n):
    headers = {"User-Agent": ua.random}
    r = requests.get(config.apis["dxy"], headers=headers)
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
            "provinces": provinces,
            "confirmeds": confirmeds,
            "suspecteds": suspecteds,
            "cureds": cureds,
            "deads": deads,
        },
        columns=["provinces", "confirmeds", "suspecteds", "cureds", "deads"],
    )
    df.to_csv("provinces_data.csv", index=False, encoding="utf8")
    confirmeds_log = np.log(np.add(confirmeds, 1))
    fig = go.Figure(
        go.Choroplethmapbox(
            featureidkey="properties.NL_NAME_1",
            geojson=provinces_map,
            locations=provinces,
            z=confirmeds_log,
            # zmin=0,
            # zmax=1000,
            zauto=True,
            colorscale="BuPu",
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
            showscale=False
        )
    )
    fig.update_layout(
        mapbox_style="carto-darkmatter",
        mapbox_zoom=3,
        mapbox_center={"lat": 35.110573, "lon": 106.493924},
        mapbox_accesstoken=config.token,
    )
    fig.update_layout(margin={"r": 0, "t": 0, "l": 0, "b": 0})
    return fig


@app.callback(
    Output("city-level-map", "figure"), [Input("interval-component", "n_intervals")]
)
def update_city_map(n):
    headers = {"User-Agent": ua.random}
    r = requests.get(config.apis["dxy"], headers=headers)
    r.raise_for_status()
    res = r.json()
    with open(
        f"data/dxy_{datetime.now().strftime('%Y%m%d')}.json",
        "w",
        encoding="utf-8",
    ) as f:
        json.dump(res, f, ensure_ascii=False, indent=4)
    data = res["data"]["getAreaStat"]
    cities, confirmeds, suspecteds, cureds, deads = [], [], [], [], []
    for province in data:
        # print(f"正在处理 {province['provinceShortName']} ...")
        if province["provinceShortName"] in municipalities:
            # print(f"直辖市：{province['provinceShortName']}")
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
            "cities": cities,
            "confirmeds": confirmeds,
            "suspecteds": suspecteds,
            "cureds": cureds,
            "deads": deads,
        }
    )
    df.to_csv("cities_data.csv", index=False, encoding="utf8")
    fig = go.Figure(
        go.Choroplethmapbox(
            featureidkey="properties.NAME",
            geojson=cities_map,
            locations=cities,
            z=confirmeds_log,
            zauto=True,
            colorscale="PuRd",
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
            showscale=False
        )
    )
    fig.update_layout(
        mapbox_style="carto-darkmatter",
        mapbox_zoom=3,
        mapbox_center={"lat": 35.110573, "lon": 106.493924},
        mapbox_accesstoken=config.token,
    )
    fig.update_layout(margin={"r": 0, "t": 0, "l": 0, "b": 0})
    return fig


if __name__ == "__main__":
    app.run_server(host="0.0.0.0", port=9102, debug=False)
