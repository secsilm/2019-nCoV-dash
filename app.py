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
import requests
from dash.dependencies import Input, Output
from plotly import tools

app = dash.Dash(__name__)
bar_colors = ["#33425b", "#5baaec", "#526ed0", "#484cb0"]
ncov_trend = pd.read_csv("ncov_trend.csv", index_col=0)
with open(".mapboxtoken", "r") as f:
    token = f.read()

with open("china.geojson") as f:
    provinces = json.load(f)
df = pd.read_csv("province_one_day_data.csv")
fig = go.Figure(
    go.Choroplethmapbox(
        featureidkey="properties.NL_NAME_1",
        geojson=provinces,
        locations=df.province,
        z=df["count"],
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

apis = {
    "qq": "https://service-n9zsbooc-1252957949.gz.apigw.tencentcs.com/release/qq",
    "dxy": "",
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
            style={"marginLeft": "1.5%", "marginRight": "1.5%", "marginBottom": ".5%"},
            children=[
                html.Div(
                    style={
                        "width": "22%",
                        "backgroundColor": "#cbd2d3",
                        "display": "inline-block",
                        "marginRight": ".8%",
                        "verticalAlign": "top",
                    },
                    children=[
                        html.H3(
                            style={
                                "textAlign": "center",
                                "fontWeight": "bold",
                                "color": "#d7191c",
                            },
                            id="confirmed-count",
                        ),
                        html.P(
                            style={
                                "textAlign": "center",
                                "fontWeight": "bold",
                                "color": "#ffffbf",
                                "padding": ".1rem",
                            },
                            children="确诊总计",
                        ),
                    ],
                ),
                html.Div(
                    style={
                        "width": "22%",
                        "backgroundColor": "#cbd2d3",
                        "display": "inline-block",
                        "marginRight": ".8%",
                        "verticalAlign": "top",
                    },
                    children=[
                        html.H3(
                            style={
                                "textAlign": "center",
                                "fontWeight": "bold",
                                "color": "#d7191c",
                            },
                            id='suspected-count',
                        ),
                        html.P(
                            style={
                                "textAlign": "center",
                                "fontWeight": "bold",
                                "color": "#ffffbf",
                                "padding": ".1rem",
                            },
                            children="疑似总计",
                        ),
                    ],
                ),
                html.Div(
                    style={
                        "width": "22%",
                        "backgroundColor": "#cbd2d3",
                        "display": "inline-block",
                        "marginRight": ".8%",
                        "verticalAlign": "top",
                    },
                    children=[
                        html.H3(
                            style={
                                "textAlign": "center",
                                "fontWeight": "bold",
                                "color": "#d7191c",
                            },
                            id='dead-count',
                        ),
                        html.P(
                            style={
                                "textAlign": "center",
                                "fontWeight": "bold",
                                "color": "#ffffbf",
                                "padding": ".1rem",
                            },
                            children="治愈总计",
                        ),
                    ],
                ),
                html.Div(
                    style={
                        "width": "22%",
                        "backgroundColor": "#cbd2d3",
                        "display": "inline-block",
                        "marginRight": ".8%",
                        "verticalAlign": "top",
                    },
                    children=[
                        html.H3(
                            style={
                                "textAlign": "center",
                                "fontWeight": "bold",
                                "color": "#d7191c",
                            },
                            id='cured-count',
                        ),
                        html.P(
                            style={
                                "textAlign": "center",
                                "fontWeight": "bold",
                                "color": "#ffffbf",
                                "padding": ".1rem",
                            },
                            children="死亡总计",
                        ),
                    ],
                ),
            ],
        ),
        dcc.Interval(id="interval-component", interval=10000 * 1000, n_intervals=0),
        dcc.Graph(id="confirmed"),
        dcc.Graph(id="dead"),
        dcc.Graph(id="map", figure=fig, style={"height": "600px"}),
    ]
)


@app.callback(
    Output("confirmed", "figure"), [Input("interval-component", "n_intervals")]
)
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

    fig = go.Figure()
    trace_confirmed = go.Scatter(
        x=dates,
        y=confirmeds,
        marker=dict(color=bar_colors[0]),
        mode="lines+markers",
        name="确诊",
    )
    trace_suspected = go.Scatter(
        x=dates,
        y=suspecteds,
        marker=dict(color=bar_colors[1]),
        mode="lines+markers",
        name="疑似",
    )

    fig.add_traces([trace_confirmed, trace_suspected])
    margin = go.layout.Margin(l=100, r=100, b=50, t=25, pad=4)
    fig["layout"].update(margin=margin, showlegend=True)
    return fig


@app.callback(Output("dead", "figure"), [Input("interval-component", "n_intervals")])
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

    fig = go.Figure()
    trace_dead = go.Scatter(
        x=dates,
        y=deads,
        marker=dict(color=bar_colors[0]),
        mode="lines+markers",
        name="死亡",
    )
    trace_cured = go.Scatter(
        x=dates,
        y=cureds,
        marker=dict(color=bar_colors[1]),
        mode="lines+markers",
        name="治愈",
    )

    fig.add_traces([trace_dead, trace_cured])
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
        Output("confirmed-count", "children"),
        Output("suspected-count", "children"),
        Output("dead-count", "children"),
        Output("cured-count", "children"),
    ],
    [Input("interval-component", "n_intervals")],
)
def update_counts(n):
    r = requests.get(apis["qq"])
    r.raise_for_status()
    res = r.json()
    confirmed = res['data']["wuwei_ww_global_vars"][0]["confirmCount"]
    suspected = res['data']["wuwei_ww_global_vars"][0]["suspectCount"]
    dead = res['data']["wuwei_ww_global_vars"][0]["deadCount"]
    cured = res['data']["wuwei_ww_global_vars"][0]["cure"]
    update_time = res['data']["wuwei_ww_global_vars"][0]["update_time"]
    return str(confirmed), str(suspected), str(dead), str(cured)


if __name__ == "__main__":
    app.run_server(host="0.0.0.0", port=9102, debug=False)
