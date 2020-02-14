# 2019-nCoV 疫情展示

本项目用于展示新型冠状病毒 2019-nCoV 疫情展示，使用 [dash](https://plot.ly/dash/) 制作。

## 使用

```bash
python app.py
```

然后打开 `http://localhost:9102/` 即可。

如果使用的是 Linux 服务器，则可以使用 gunicorn 来部署：

```bash
gunicorn -c config.py app:server
```

同时修改 [`logging_config.yml`](./logging_config.yml) 中的 `loggers`，将 `__main__` 修改为 `app` 即可。

![homepage](./screenshots/homepage.png)

## References

- [Mapbox Map Layers | Python | Plotly](https://plot.ly/python/mapbox-layers/)
- [Mapbox Choropleth Maps | Python | Plotly](https://plot.ly/python/mapbox-county-choropleth/#choropleth-map-using-plotlygraphobjects-and-carto-base-map-no-token-needed)