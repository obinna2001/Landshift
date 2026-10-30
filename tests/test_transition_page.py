"""Exercise selected-period downloads against small, aligned study rasters."""

import base64
import csv
from html import unescape
import io
from pathlib import Path
import re

import numpy as np
import pandas as pd
from rasterio.transform import from_origin
import pytest
from streamlit.testing.v1 import AppTest

from land_cover_change.app.components.transition_analysis import (
    build_transition_content,
    build_transition_csv,
)
from land_cover_change.config.config import DynamicWorldClass, resolved_config


APP = Path(__file__).resolve().parents[1] / "src/land_cover_change/app/main.py"


def test_transition_csv_uses_common_valid_pixels_and_square_kilometres(raster_factory):
    arguments = dict(crs="EPSG:32631", transform=from_origin(300000, 700000, 10, 10))
    earlier = raster_factory("lulc_2016.tif", np.array([[1, 1], [6, 255]], dtype="uint8"), **arguments)
    later = raster_factory("lulc_2025.tif", np.array([[1, 6], [255, 6]], dtype="uint8"), **arguments)
    names = {1: "Trees", 6: "Built area", 8: "Snow and ice"}
    rows = list(csv.DictReader(io.StringIO(build_transition_csv(earlier, later, names))))
    assert list(rows[0]) == ["Earlier class / Later class", *names.values()]
    assert [row["Earlier class / Later class"] for row in rows] == list(names.values())
    assert float(rows[0]["Trees"]) == pytest.approx(.0001)
    assert float(rows[0]["Built area"]) == pytest.approx(.0001)
    assert sum(float(row[label]) for row in rows for label in names.values()) == pytest.approx(.0002)
    assert all(float(rows[2][label]) == 0 for label in names.values())


def test_period_control_keeps_selection_and_download_is_deferred(raster_factory, tmp_path, monkeypatch):
    arguments = dict(crs="EPSG:32631", transform=from_origin(300000, 700000, 10, 10))
    for year, pixels in (
        (2016, [[1, 1], [1, 6]]),
        (2020, [[1, 1], [6, 6]]),
        (2025, [[1, 6], [6, 6]]),
    ):
        raster_factory(f"lulc_{year}.tif", np.array(pixels, dtype="uint8"), **arguments)
    monkeypatch.setattr(resolved_config.dataset.raw_dataset, "aoi_lulc", str(tmp_path))
    app = AppTest.from_file(str(APP), default_timeout=30).run()
    app.switch_page("views/transition_analysis.py").run()
    assert not app.exception
    periods = app.button_group(key="transition-period")
    assert periods.options == ["2016–2020", "2020–2025", "2016–2025"]
    assert periods.value == "2016–2025"
    download = app.get("download_button")[0].proto
    assert download.label == "Download matrix ↓"
    assert download.deferred_file_id
    original_id = download.deferred_file_id
    initial = transition_html(app)
    assert 'data-period="2016–2025"' in initial
    assert stat_value(initial, "changed") == pytest.approx(.0002)
    assert stat_value(initial, "retained") == pytest.approx(.0002)
    assert embedded_csv(initial)["Trees"]["Built area"] == pytest.approx(.0002)
    assert 'download="study-transitions-2016-2025.csv"' in initial
    periods.set_value("2020–2025").run()
    assert not app.exception
    assert app.button_group(key="transition-period").value == "2020–2025"
    assert app.get("download_button")[0].proto.deferred_file_id != original_id
    changed = transition_html(app)
    assert 'data-period="2020–2025"' in changed
    assert stat_value(changed, "changed") == pytest.approx(.0001)
    assert stat_value(changed, "retained") == pytest.approx(.0003)
    assert embedded_csv(changed)["Trees"]["Built area"] == pytest.approx(.0001)
    assert 'download="study-transitions-2020-2025.csv"' in changed
    app.run()
    assert app.button_group(key="transition-period").value == "2020–2025"


def transition_html(app):
    return next(element.value for element in app.markdown
                if '<div class="transition-analysis-content"' in element.value)


def stat_value(html, key):
    return float(re.search(
        rf'data-stat="{key}".*?data-area-km2="([^"]+)"', html,
    ).group(1))


def embedded_csv(html):
    encoded = re.search(r'data:text/csv;charset=utf-8;base64,([^"]+)', html).group(1)
    rows = csv.DictReader(io.StringIO(base64.b64decode(encoded).decode()))
    return {
        row["Earlier class / Later class"]: {name: float(value) for name, value in row.items()
                                              if name != "Earlier class / Later class"}
        for row in rows
    }


@pytest.fixture
def selected_matrix():
    ids = [1, 5, 6, 8]
    matrix = pd.DataFrame(
        [[8.12345678, 1, 4.123456789, 0], [2, 3, 1, 0], [.5, .25, 20, 0], [0, 0, 0, 0]],
        index=ids, columns=ids,
    )
    classes = {
        1: DynamicWorldClass(name="trees", colour="#397D49"),
        5: DynamicWorldClass(name="shrub and scrub", colour="#DFC35A"),
        6: DynamicWorldClass(name="built area", colour="#C4281B"),
        8: DynamicWorldClass(name="snow and ice", colour="#B39FE1"),
    }
    return matrix, classes


def test_transition_content_conserves_area_and_excludes_persistence_from_ranking(selected_matrix):
    matrix, classes = selected_matrix
    html = build_transition_content(matrix, classes, (2016, 2025))
    assert stat_value(html, "changed") == pytest.approx(8.873456789)
    assert stat_value(html, "retained") == pytest.approx(31.12345678)
    assert stat_value(html, "changed") + stat_value(html, "retained") == pytest.approx(matrix.to_numpy().sum())
    assert stat_value(html, "largest") == pytest.approx(4.123456789)
    assert 'Trees → Built area was the largest mapped conversion' in html
    ranking = re.findall(r'class="bar-row" data-from-class="(\d+)" data-to-class="(\d+)" data-area-km2="([^"]+)"', html)
    assert len(ranking) == 5
    assert [(earlier, later) for earlier, later, _ in ranking][0] == ("1", "6")
    assert all(earlier != later for earlier, later, _ in ranking)
    assert [float(value) for _, _, value in ranking] == sorted((float(value) for _, _, value in ranking), reverse=True)
    assert 'background:#C4281B' in html
    assert 'data-from-class="6" data-to-class="6" data-area-km2="20"' in html
    assert '<td data-to-class="6">4.12</td>' in html
    assert 'Snow &amp; ice' not in html
    assert embedded_csv(html)["Trees"]["Built area"] == 4.123456789
    assert embedded_csv(html)["Snow and ice"]["Snow and ice"] == 0


@pytest.mark.parametrize("area", [0, 2])
def test_transition_content_handles_no_conversions_without_a_fictitious_largest_pair(selected_matrix, area):
    matrix, classes = selected_matrix
    matrix.loc[:, :] = 0
    matrix.loc[1, 1] = area
    html = build_transition_content(matrix, classes, (2016, 2025))
    assert stat_value(html, "changed") == 0
    assert stat_value(html, "retained") == area
    assert stat_value(html, "largest") == 0
    assert 'class="bar-row"' not in html
    assert 'No mapped class conversions were observed' in html
    assert 'was the largest mapped conversion' not in html
    assert 'nan' not in html.lower() and 'infinity' not in html.lower()


def test_transition_content_escapes_registry_labels(selected_matrix):
    matrix, classes = selected_matrix
    classes[1].name = 'trees <script>alert("x")</script> & water'
    html = build_transition_content(matrix, classes, (2016, 2025))
    assert '<script>' not in html
    assert '&lt;script&gt;' in html and '&amp; water' in html
    assert 'Trees <script>' in unescape(re.search(r'class="bar-label">(.*?)</span>', html).group(1))


def test_transition_page_reports_misaligned_selected_rasters(raster_factory, tmp_path, monkeypatch):
    for year, x in ((2016, 300000), (2025, 300010)):
        raster_factory(
            f"lulc_{year}.tif", np.array([[1, 6]], dtype="uint8"),
            crs="EPSG:32631", transform=from_origin(x, 700000, 10, 10),
        )
    monkeypatch.setattr(resolved_config.dataset.raw_dataset, "aoi_lulc", str(tmp_path))
    app = AppTest.from_file(str(APP), default_timeout=30).run()
    app.switch_page("views/transition_analysis.py").run()
    assert not app.exception
    assert any("selected transition period could not be prepared" in error.value for error in app.error)
    assert all('<div class="transition-analysis-content"' not in element.value for element in app.markdown)


@pytest.mark.parametrize("file_count", [0, 1])
def test_period_toolbar_reports_insufficient_study_data(file_count, raster_factory, tmp_path, monkeypatch):
    if file_count:
        raster_factory("lulc_2025.tif", np.array([[1, 6]], dtype="uint8"))
    monkeypatch.setattr(resolved_config.dataset.raw_dataset, "aoi_lulc", str(tmp_path))
    app = AppTest.from_file(str(APP), default_timeout=30).run()
    app.switch_page("views/transition_analysis.py").run()
    assert not app.exception
    assert app.info
    assert not app.button_group
    assert not app.get("download_button")
