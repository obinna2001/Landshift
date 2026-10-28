"""Exercise selected-period downloads against small, aligned study rasters."""

import csv
import io
from pathlib import Path

import numpy as np
from rasterio.transform import from_origin
import pytest
from streamlit.testing.v1 import AppTest

from land_cover_change.app.components.transition_analysis import build_transition_csv
from land_cover_change.config.config import resolved_config


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
    for year in (2016, 2020, 2025):
        raster_factory(f"lulc_{year}.tif", np.array([[1, 1], [1, 6]], dtype="uint8"))
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
    periods.set_value("2020–2025").run()
    assert not app.exception
    assert app.button_group(key="transition-period").value == "2020–2025"
    assert app.get("download_button")[0].proto.deferred_file_id != original_id
    app.run()
    assert app.button_group(key="transition-period").value == "2020–2025"


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
