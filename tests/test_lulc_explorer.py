import base64
import csv
from html import unescape
import io
from pathlib import Path
import re

import numpy as np
import pandas as pd
import pytest

from land_cover_change.app.components.area_analysis import (
    build_class_chart,
    build_comparison_details,
    build_download_table,
    build_explorer_map,
    build_explorer_legend,
    describe_composition,
    discover_year_paths,
)
from land_cover_change.config.config import DynamicWorldClass
from land_cover_change.services.raster import RasterMapOverlay


@pytest.fixture
def classes():
    return {
        1: DynamicWorldClass(name="trees", colour="#397D49"),
        5: DynamicWorldClass(name="shrub and scrub", colour="#DFC35A"),
        6: DynamicWorldClass(name="built area", colour="#C4281B"),
    }


@pytest.fixture
def areas():
    rows = []
    for year, values in ((2016, [70, 10, 20]), (2020, [60, 10, 30]), (2025, [40, 10, 50])):
        for class_value, value in zip((1, 5, 6), values):
            rows.append({"year": year, "class_value": class_value, "area_km2": value / 10,
                         "class_percentage": float(value), "pixel_count": value})
    return pd.DataFrame(rows)


def test_discover_paths_returns_sorted_unique_observation_years(raster_factory, tmp_path):
    raster_factory("lulc_2025.tif", np.array([[1]], dtype="uint8"))
    raster_factory("lulc_2016.tif", np.array([[1]], dtype="uint8"))
    assert list(discover_year_paths(tmp_path)) == [2016, 2025]
    raster_factory("other_2016.tif", np.array([[1]], dtype="uint8"))
    with pytest.raises(ValueError, match="Multiple.*2016"):
        discover_year_paths(tmp_path)


def test_compared_maps_include_keyless_osm_synchronization_and_per_map_controls(classes):
    overlay = RasterMapOverlay(
        image=np.full((3, 3, 4), 255, dtype=np.uint8),
        bounds=((6.4, 5.6), (6.5, 5.7)),
    )
    html, height = build_explorer_map({2016: overlay, 2025: overlay}, classes, opacity=0.5)
    assert html.count("L.map(") == 2
    assert html.count("L.tileLayer(") == 2
    assert html.count("https://tile.openstreetmap.org/{z}/{x}/{y}.png") == 2
    assert "www.openstreetmap.org/copyright" in html
    assert "OpenStreetMap" in html and "contributors" in html
    assert "CARTO" not in html and "cartocdn.com" not in html
    assert "?key=" not in html
    assert "lulc-map-legend" not in html
    assert "dynamic-world-legend" not in html
    assert "node.innerHTML = '<strong>2016</strong>'" in html
    assert "node.innerHTML = '<strong>2025</strong>'" in html
    assert "Jan–Feb composite" not in html
    assert "Reset extent" not in html and "lulc-map-reset" not in html
    assert "target.setView(source.getCenter(), source.getZoom()" in html
    assert '"opacity": 0.5' in html
    classes[1].name = "trees <water & land>"
    legend_html = build_explorer_legend(classes)
    assert legend_html.count('<section class="lulc-shared-legend"') == 1
    assert legend_html.count("<li ") == len(classes)
    assert "Trees &lt;water &amp; land&gt;" in legend_html
    assert "Shrub and scrub" in legend_html
    assert "#397D49" in legend_html
    assert height == 600


def test_single_map_does_not_include_a_comparison_synchronizer(classes):
    overlay = RasterMapOverlay(np.full((2, 2, 4), 255, dtype=np.uint8), ((6.4, 5.6), (6.5, 5.7)))
    html, _ = build_explorer_map({2020: overlay}, classes)
    assert html.count("L.map(") == 1
    assert "synchronizing" not in html
    assert html.count("L.tileLayer(") == 1
    assert "https://tile.openstreetmap.org/{z}/{x}/{y}.png" in html
    assert "cartocdn.com" not in html
    assert "L.imageOverlay(" in html
    assert "map.invalidateSize({pan:false})" in html
    assert "Reset extent" not in html and "lulc-map-reset" not in html
    with pytest.raises(ValueError, match="one or two"):
        build_explorer_map({}, classes)
    with pytest.raises(ValueError, match="opacity"):
        build_explorer_map({2020: overlay}, classes, opacity=2)


def test_chart_uses_selected_years_and_explicit_units(areas, classes):
    share = build_class_chart(areas, classes, [2016, 2025], unit="share")
    assert "2020" not in share
    assert "70.00 %" in share and "40.00 %" in share
    assert "#397D49" in share
    area = build_class_chart(areas, classes, [2020], unit="area")
    assert "6.00 km²" in area
    assert "2016" not in area and "2025" not in area
    with pytest.raises(ValueError, match="unit"):
        build_class_chart(areas, classes, [2020], unit="invalid")


def test_download_has_selected_years_and_correct_signed_change(areas, classes):
    output = build_download_table(areas, classes, [2016, 2025])
    assert "2020" not in " ".join(output.columns)
    assert output.loc[output["Class"] == "Trees", "2016–2025 change (km²)"].item() == -3
    assert output.loc[output["Class"] == "Built area", "2016–2025 change (km²)"].item() == 3
    assert len(build_download_table(areas, classes, [2020]).columns) == 3



def test_comparison_details_format_display_and_keep_full_precision_csv(areas, classes):
    areas.loc[(areas["year"] == 2016) & (areas["class_value"] == 6), "area_km2"] = 1234.56789
    classes[1].name = "trees <water & land>"
    html = build_comparison_details(areas, classes, [2016, 2025])
    assert '<summary>Inspect the comparison table and calculation notes</summary>' in html
    assert '<td>1,234.57</td>' in html
    assert '<td>−3.00</td>' in html
    assert '<td>+0.00</td>' in html
    assert 'Trees &lt;water &amp; land&gt;' in html
    assert 'Shrub &amp; scrub' in html
    assert 'Download selected comparison (CSV) ↓' in html
    assert 'download="class-areas-2016-2025.csv"' in html
    encoded = re.search(r'href="data:text/csv;charset=utf-8;base64,([^"]+)"', html).group(1)    #type: ignore
    rows = list(csv.DictReader(io.StringIO(base64.b64decode(encoded).decode("utf-8"))))
    assert list(rows[0]) == ["Land-cover class", "2016 · km²", "2016 · %", "2025 · km²", "2025 · %", "2016–2025 · km² change"]
    assert [row["Land-cover class"] for row in rows] == ["Built area", "Trees <water & land>", "Shrub & scrub"]
    assert float(rows[0]["2016 · km²"]) == 1234.56789
    assert float(rows[1]["2016–2025 · km² change"]) == -3


def test_single_year_details_have_only_selected_year_columns_and_no_change(areas, classes):
    html = build_comparison_details(areas, classes, [2020])
    assert '<summary>Inspect the selected-year table and calculation notes</summary>' in html
    assert 'Download selected-year areas (CSV) ↓' in html
    headers = [unescape(value) for value in re.findall(r'<th\b[^>]*>(.*?)</th>', html)]
    assert headers == ["Land-cover class", "2020 · km²", "2020 · %"]
    encoded = re.search(r'href="data:text/csv;charset=utf-8;base64,([^"]+)"', html).group(1)    #type: ignore
    rows = list(csv.DictReader(io.StringIO(base64.b64decode(encoded).decode("utf-8"))))
    assert list(rows[0]) == headers
    assert len(rows) == len(classes)


def test_comparison_narrative_matches_the_wireframe(areas, classes):
    assert describe_composition(areas, classes, [2016, 2020]) == (
        "Between 2016 and 2020, built area expanded by 1.00 km², moving from 2.00 km² (20.0%) "
        "to 3.00 km² (30.0%). Over the same interval, tree cover decreased by 1.00 km², "
        "from 7.00 km² to 6.00 km².",
        "Shrub and scrub increased by 0.00 km², from 1.00 km² to 1.00 km², accounting for "
        "10.0% of the mapped area by 2020. The largest mapped class at both endpoints was trees.",
    )


def test_snapshot_narrative_matches_the_wireframe_with_full_study_context(areas, classes):
    assert describe_composition(areas, classes, [2020]) == (
        "In 2020, built area occupied 3.00 km² (30.0% of the mapped area), while tree cover "
        "occupied 6.00 km² (60.0%). Shrub and scrub accounted for a further 1.00 km² (10.0%).",
        "Across the full 2016–2025 study period, built area increased by 3.00 km² and tree cover "
        "decreased by 3.00 km². Shrub and scrub increased by 0.00 km², reaching 1.00 km² in 2025. "
        "This study-wide context complements the selected-year snapshot above.",
    )


def test_narrative_handles_contraction_and_a_change_in_dominance(areas, classes):
    # Equal areas use the wireframe's class ordering, where built area comes first.
    areas.loc[(areas["year"] == 2025) & (areas["class_value"] == 1), "area_km2"] = 5
    first, second = describe_composition(areas, classes, [2016, 2025])
    assert "The largest mapped class shifted from trees in 2016 to built area in 2025." in second
    first, second = describe_composition(areas, classes, [2025, 2016])
    assert "built area contracted by 3.00 km²" in first
    assert "tree cover increased by 2.00 km²" in first
    assert "The largest mapped class shifted from built area in 2025 to trees in 2016." in second
