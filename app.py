"""
关于 [mapbox_style](https://plot.ly/python/mapbox-layers/)：

The accepted values for layout.mapbox.style are one of:

- "white-bg" yields an empty white canvas which results in no external HTTP requests
"open-street-map", "carto-positron", "carto-darkmatter", "stamen-terrain", "stamen-toner" or "stamen-watercolor" yeild maps composed of raster tiles from various public tile servers which do not require signups or access tokens

- "basic", "streets", "outdoors", "light", "dark", "satellite", or "satellite-streets" yeild maps composed of vector tiles from the Mapbox service, and do require a Mapbox Access Token or an on-premise Mapbox installation.

- A Mapbox service style URL, which requires a Mapbox Access Token or an on-premise Mapbox installation.

- A Mapbox Style object as defined at https://docs.mapbox.com/mapbox-gl-js/style-spec/
"""

import json
from datetime import datetime

import dash
import dash_core_components as dcc
import dash_html_components as html
import dash_daq as daq
import dash_table
import numpy as np
import pandas as pd
import plotly.graph_objs as go
from plotly.subplots import make_subplots
import requests
from dash.dependencies import Input, Output
from plotly import tools

app = dash.Dash(__name__)
colors = ["#E51017", "#FFF210", "#0AFC6F", "#0A0603"]
with open(".mapboxtoken", "r") as f:
    token = f.read()

with open("china.geojson") as f:
    provinces_map = json.load(f)

apis = {
    "qq": "https://service-n9zsbooc-1252957949.gz.apigw.tencentcs.com/release/qq",
    "dxy": "https://service-0gg71fu4-1252957949.gz.apigw.tencentcs.com/release/dingxiangyuan",
    "province_city_history": "http://ncov.nosensor.com:8080/api/",
}


def timestamp2datetime(t):
    return pd.datetime.fromtimestamp(t).strftime("%Y-%m-%d %H:%M:%S")


app.title = f"新型冠状病毒 2019-nCoV 疫情趋势"
app.layout = html.Div(
    [
        html.H1(children=f"新型冠状病毒 2019-nCoV 疫情趋势", style={"margin-left": "20px"}),
        html.Div(id="update-time-text", style={"margin-left": "20px"}),
        html.Div(
            id="number_plate",
            style={
                "marginLeft": "1.5%",
                "marginRight": "1.5%",
                "marginBottom": ".5%",
                "marginTop": ".5%",
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
                        )
                    ],
                ),
            ],
        ),
        dcc.Interval(id="interval-component", interval=10 * 60 * 1000, n_intervals=0),
        dcc.Graph(id="trend"),
        dcc.Graph(
            id="map",
            style={
                "height": "600px",
                "width": "90%",
                "marginRight": "5%",
                "marginLeft": "5%",
            },
        ),
    ]
)


@app.callback(Output("trend", "figure"), [Input("interval-component", "n_intervals")])
def update_graph(n):
    r = requests.get(apis["qq"])
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
        name="确诊",
    )
    trace_suspected = go.Scatter(
        x=dates,
        y=suspecteds,
        marker=dict(color=colors[1]),
        mode="lines+markers",
        name="疑似",
    )
    trace_dead = go.Scatter(
        x=dates, y=deads, marker=dict(color=colors[2]), mode="lines+markers", name="死亡",
    )
    trace_cured = go.Scatter(
        x=dates,
        y=cureds,
        marker=dict(color=colors[3]),
        mode="lines+markers",
        name="治愈",
    )

    fig.append_trace(trace_confirmed, 1, 1)
    fig.append_trace(trace_suspected, 1, 1)
    fig.append_trace(trace_dead, 2, 1)
    fig.append_trace(trace_cured, 2, 1)
    margin = go.layout.Margin(l=100, r=100, b=50, t=25, pad=4)
    fig["layout"].update(margin=margin, showlegend=True)
    return fig


@app.callback(
    Output("update-time-text", "children"), [Input("interval-component", "n_intervals")]
)
def update_time(n):
    return f'更新时间：{datetime.now().strftime("%Y-%m-%d %H:%M:%S")}'


@app.callback(
    [
        Output("confirmed-count", "value"),
        Output("suspected-count", "value"),
        Output("dead-count", "value"),
        Output("cured-count", "value"),
    ],
    [Input("interval-component", "n_intervals")],
)
def update_counts(n):
    r = requests.get(apis["qq"])
    r.raise_for_status()
    res = r.json()
    confirmed = res["data"]["wuwei_ww_global_vars"][0]["confirmCount"]
    suspected = res["data"]["wuwei_ww_global_vars"][0]["suspectCount"]
    dead = res["data"]["wuwei_ww_global_vars"][0]["deadCount"]
    cured = res["data"]["wuwei_ww_global_vars"][0]["cure"]
    update_time = res["data"]["wuwei_ww_global_vars"][0]["update_time"]
    return f"{confirmed:05d}", f"{suspected:05d}", f"{dead:05d}", f"{cured:05d}"


@app.callback(Output("map", "figure"), [Input("interval-component", "n_intervals")])
def update_map(n):
    # df = pd.read_csv("test/province_one_day_data.csv")
    r = requests.get(apis["dxy"])
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
        }
    )

    fig = go.Figure(
        go.Choroplethmapbox(
            featureidkey="properties.NL_NAME_1",
            geojson=provinces_map,
            locations=df.provinces,
            z=df.confirmeds,
            colorscale="Reds",
            zmin=0,
            zmax=1000,
            # zauto=True,
            marker_opacity=0.5,
            marker_line_width=0,
        )
    )
    fig.update_layout(
        mapbox_style="carto-darkmatter",
        mapbox_zoom=3,
        mapbox_center={"lat": 35.110573, "lon": 106.493924},
        mapbox_accesstoken=token,
    )
    fig.update_layout(margin={"r": 0, "t": 0, "l": 0, "b": 0})
    return fig


if __name__ == "__main__":
    app.run_server(host="0.0.0.0", port=9102, debug=False)
