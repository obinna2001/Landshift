"""Exercise the page controls against small, deterministic raster fixtures."""

from html import unescape
from pathlib import Path
import re

import numpy as np
import pytest
from streamlit.testing.v1 import AppTest

from land_cover_change.config.config import resolved_config


APP = Path(__file__).resolve().parents[1] / "src/land_cover_change/app/main.py"


def comparison_table(app):
    details = next(element.value for element in app.markdown
                   if '<details class="lulc-data-details">' in element.value)
    headers = [unescape(value) for value in re.findall(r'<th\b[^>]*>(.*?)</th>', details)]
    body = details.split("<tbody>", 1)[1].split("</tbody>", 1)[0]
    rows = [[unescape(value) for value in re.findall(r'<td>(.*?)</td>', row)]
            for row in re.findall(r'<tr>(.*?)</tr>', body)]
    return headers, rows


@pytest.fixture
def explorer(raster_factory, tmp_path, monkeypatch):
    for year, pixels in (
        (2016, [[1, 1], [1, 6]]),
        (2020, [[1, 1], [6, 6]]),
        (2025, [[1, 6], [6, 6]]),
    ):
        raster_factory(f"lulc_{year}.tif", np.array(pixels, dtype="uint8"))
    monkeypatch.setattr(resolved_config.dataset.raw_dataset, "aoi_lulc", str(tmp_path))
    app = AppTest.from_file(str(APP), default_timeout=30).run()
    app.switch_page("views/map.py").run()
    assert not app.exception
    assert all("API key" not in notice.value for notice in app.info)
    shared_legends = [element.proto.body for element in app.get("html")
                      if '<section class="lulc-shared-legend"' in element.proto.body]
    assert len(shared_legends) == 1
    assert shared_legends[0].count("<li ") == len(resolved_config.dynamic_world.classes) - 1
    assert "Snow and ice" not in shared_legends[0]
    assert "lulc-map-legend" not in app.get("iframe")[0].proto.srcdoc
    assert all("Uteh, Iwogban and environs" not in element.proto.body
               for element in app.get("html"))
    return app


def test_selected_years_update_the_map_and_analysis_together(explorer):
    app = explorer
    assert app.selectbox(key="lulc-view-mode").value == "Compare years"
    assert app.selectbox(key="lulc-earlier-year").value == 2016
    assert app.selectbox(key="lulc-later-year").value == 2025
    headers, rows = comparison_table(app)
    assert "2016 · km²" in headers
    assert "2025 · km²" in headers
    assert len(rows) == 8
    assert rows[0][0] == "Built area"
    assert not app.dataframe
    app.selectbox(key="lulc-earlier-year").select(2020).run()
    assert not app.exception
    assert app.selectbox(key="lulc-later-year").options == ["2025"]
    headers, _ = comparison_table(app)
    assert "2016 · km²" not in headers
    assert "2020 · km²" in headers
    app.selectbox(key="lulc-view-mode").select("Single year").run()
    app.selectbox(key="lulc-study-year").select(2020).run()
    assert not app.exception
    headers, _ = comparison_table(app)
    assert headers == ["Land-cover class", "2020 · km²", "2020 · %"]
    assert app.get("iframe")[0].proto.srcdoc.count("L.map(") == 1
    assert sum('<section class="lulc-shared-legend"' in element.proto.body
               for element in app.get("html")) == 1


def test_reset_extent_and_unit_switch_keep_selected_data(explorer):
    app = explorer
    original = comparison_table(app)
    original_map = app.get("iframe")[0].proto.srcdoc
    app.button_group(key="lulc-area-unit").set_value("Area (km²)").run()
    assert not app.exception
    assert comparison_table(app) == original
    assert app.get("iframe")[0].proto.srcdoc == original_map
    app.button[0].click().run()
    assert not app.exception
    assert app.session_state["lulc-extent-revision"] == 1
    assert "extent-revision:1" in app.get("iframe")[0].proto.srcdoc
