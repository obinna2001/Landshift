"""Map and class-area presentation helpers for the LULC explorer page."""

import base64
from collections.abc import Mapping, Sequence
from html import escape
import math
from pathlib import Path

from branca.element import Element, Figure, MacroElement, Template
import folium
import pandas as pd

from land_cover_change.app.components.map_legend import build_dynamic_world_legend
from land_cover_change.config.config import DynamicWorldClass
from land_cover_change.data_access.raster import discover_lulc_rasters
from land_cover_change.services.raster import RasterMapOverlay
from land_cover_change.utils.utils import extract_year


def discover_year_paths(directory: str | Path) -> dict[int, Path]:
    """Find annual rasters, rejecting ambiguous duplicate observation years."""
    paths: dict[int, Path] = {}
    for path in discover_lulc_rasters(directory):
        year = extract_year(path)
        if year in paths:
            raise ValueError(f"Multiple land-cover rasters represent {year}")
        paths[year] = path
    return dict(sorted(paths.items()))


def build_explorer_legend(classes: Mapping[int, DynamicWorldClass]) -> str:
    """Render one shared class key below the maps using the registry palette."""
    build_dynamic_world_legend(classes)
    items = "".join(
        f'<li data-class-value="{class_value}">'
        '<span class="lulc-legend-swatch" aria-hidden="true" '
        f'style="background-color:{escape(definition.colour, quote=True)};"></span>'
        f'<span class="lulc-legend-label">{escape(definition.name.capitalize())}</span></li>'
        for class_value, definition in sorted(classes.items())
    )
    return (
        '<section class="lulc-shared-legend" aria-label="Land-cover legend">'
        '<p class="lulc-legend-title">Land-cover legend</p>'
        f'<ul>{items}</ul></section>'
    )


def _map_controls(map_: folium.Map, year: int) -> None:
    """Mount a year label and keep the map sized to its container."""
    controls = MacroElement()
    controls._name = "ExplorerControls"
    controls._template = Template(
        """
        {% macro script(this, kwargs) %}
        (function () {
            var map = {{ this._parent.get_name() }};
            var stamp = L.control({position: 'topleft'});
            stamp.onAdd = function () {
                var node = L.DomUtil.create('div', 'lulc-map-stamp');
                node.innerHTML = '<strong>{{ this.year }}</strong>';
                L.DomEvent.disableClickPropagation(node);
                return node;
            };
            stamp.addTo(map);
            window.addEventListener('resize', function () {
                map.invalidateSize({pan:false});
            });
        }());
        {% endmacro %}
        """
    )
    controls.year = year
    controls.add_to(map_)


def build_explorer_map(
    overlays: Mapping[int, RasterMapOverlay],
    classes: Mapping[int, DynamicWorldClass],
    *,
    opacity: float = 0.86,
) -> tuple[str, int]:
    """Render one or two synchronized OpenStreetMap maps with local raster overlays.

    The supplied images must already be prepared on the EPSG:3857 grid by
    ``prepare_map_overlay``. Every map has its own year label and attribution.
    A shared legend can be rendered after the map document.
    Standard OpenStreetMap tiles provide a keyless basemap for every map.
    """
    if not 1 <= len(overlays) <= 2:
        raise ValueError("Select one or two observation years")
    if not isinstance(opacity, (float, int)) or isinstance(opacity, bool) or not 0 <= opacity <= 1:
        raise ValueError("opacity must be between zero and one")
    # Validate registry names and colours using the established shared component.
    build_dynamic_world_legend(classes)
    height = 600
    figure = Figure(width="100%", height=height)
    figure.header.add_child(Element(
        """<style>
        html, body { width:100%; height:100%; margin:0; padding:0; }
        body { display:grid; grid-template-columns:repeat(COUNT,minmax(0,1fr));
          gap:16px; background:#fff; overflow:hidden; }
        .folium-map { width:100% !important; height:100% !important;
          position:relative !important; top:0 !important; left:0 !important; min-width:0; }
        .leaflet-container { background:#eef1eb; }
        .lulc-map-stamp { background:rgba(255,255,255,.95); padding:11px 14px;
          border:1px solid #d9dfd3; border-radius:3px; color:#16264a;
          font:12px/1.5 system-ui,sans-serif; box-shadow:0 1px 4px #18251e12; }
        .lulc-map-stamp strong { display:block; font-size:19px; font-weight:600; }
        .leaflet-control-attribution { font-size:9px !important; }
        @media(max-width:760px) {
          body { grid-template-columns:minmax(0,1fr); grid-template-rows:repeat(COUNT,minmax(0,1fr)); gap:11.2px; }
          .lulc-map-stamp { padding:6px 10px; }
          .lulc-map-stamp strong { font-size:15px; }
        }
        </style>""".replace("COUNT", str(len(overlays)))
    ))
    maps = []
    for year, overlay in sorted(overlays.items()):
        south_west, north_east = overlay.bounds
        map_ = folium.Map(
            location=[(south_west[0] + north_east[0]) / 2, (south_west[1] + north_east[1]) / 2],
            tiles=None,
            zoom_control=True,
            control_scale=True,
            prefer_canvas=True,
        )
        map_.add_to(figure)
        folium.TileLayer(
            tiles="https://tile.openstreetmap.org/{z}/{x}/{y}.png",
            attr='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors',
            name="OpenStreetMap",
            max_zoom=19,
            control=False,
        ).add_to(map_)
        folium.raster_layers.ImageOverlay(
            overlay.image,
            bounds=overlay.bounds,
            name=f"Dynamic World {year}",
            opacity=opacity,
            pixelated=True,
            mercator_project=False,
            interactive=False,
        ).add_to(map_)
        map_.fit_bounds(overlay.bounds, padding=[24, 24])
        _map_controls(map_, year)
        maps.append(map_)
    if len(maps) == 2:
        synchronization = MacroElement()
        synchronization._template = Template("""
        {% macro script(this, kwargs) %}
        (function () {
            var maps = [{{ this.first }}, {{ this.second }}];
            var synchronizing = false;
            function follow(source, target) {
                source.on('moveend', function () {
                    if (synchronizing) return;
                    synchronizing = true;
                    try { target.setView(source.getCenter(), source.getZoom(), {animate:false}); }
                    finally { synchronizing = false; }
                });
            }
            follow(maps[0], maps[1]); follow(maps[1], maps[0]);
        }());
        {% endmacro %}
        """)
        synchronization.first = maps[0].get_name()
        synchronization.second = maps[1].get_name()
        figure.add_child(synchronization)
    return figure.render(), height


def _selected_rows(table: pd.DataFrame, years: Sequence[int]) -> pd.DataFrame:
    if not 1 <= len(years) <= 2 or len(set(years)) != len(years):
        raise ValueError("Select one or two distinct observation years")
    selected = table.loc[table["year"].isin(years)].copy()
    if set(selected["year"].unique()) != set(years):
        raise ValueError("Area data is missing a selected year")
    return selected


def build_class_chart(
    table: pd.DataFrame,
    classes: Mapping[int, DynamicWorldClass],
    years: Sequence[int],
    *,
    unit: str = "area",
) -> str:
    """Build the wireframe's per-class, per-year horizontal comparison bars."""
    if unit not in {"area", "share"}:
        raise ValueError("unit must be 'area' or 'share'")
    selected = _selected_rows(table, years)
    measurement = "area_km2" if unit == "area" else "class_percentage"
    present = sorted(selected.loc[selected["area_km2"] > 0, "class_value"].unique())
    maximum = float(selected[measurement].max())
    domain = 100.0 if unit == "share" else max(10.0, math.ceil(maximum / 10) * 10)
    axis = "".join(f"<span>{domain * fraction:g}{'%' if unit == 'share' else ''}</span>" for fraction in (0, .25, .5, .75, 1))
    rows = []
    for value in present:
        definition = classes[int(value)]
        bars = []
        for year in years:
            row = selected.loc[(selected["year"] == year) & (selected["class_value"] == value)]
            amount = float(row[measurement].iloc[0]) if not row.empty else 0.0
            label = f"{amount:.2f} {'km²' if unit == 'area' else '%'}"
            title = escape(f"{definition.name.capitalize()} · {year}: {label}", quote=True)
            bars.append(
                '<div class="lulc-class-bar-line">'
                f'<span class="lulc-class-year">{year}</span>'
                '<div class="lulc-class-bar-track">'
                f'<div class="lulc-class-bar-fill" style="width:{amount / domain * 100:.4f}%;'
                f'background-color:{escape(definition.colour, quote=True)};" title="{title}"></div></div>'
                f'<span class="lulc-class-bar-value">{label}</span></div>'
            )
        rows.append(
            '<div class="lulc-class-comparison-row">'
            f'<div class="lulc-comparison-class-name">{escape(definition.name.capitalize())}</div>'
            '<div class="lulc-class-year-bars">' + "".join(bars) + '</div></div>'
        )
    unit_note = "Shares are percentages of valid mapped area." if unit == "share" else "Areas are measured in square kilometres."
    return (
        '<div class="lulc-class-comparison-chart" role="group" aria-label="Class area comparison">'
        '<div class="lulc-class-chart-axis" aria-hidden="true">' + axis + '</div>'
        + "".join(rows) + '</div>'
        '<p class="lulc-chart-caption">Colours identify land-cover classes. Each bar is labelled '
        f'with its study year. {unit_note}</p>'
    )


def build_download_table(
    table: pd.DataFrame,
    classes: Mapping[int, DynamicWorldClass],
    years: Sequence[int],
) -> pd.DataFrame:
    """Create an explicit selected-year CSV table, including zero-area classes."""
    selected = _selected_rows(table, years)
    output = pd.DataFrame({"Class": [classes[value].name.capitalize() for value in sorted(classes)]}, index=sorted(classes))
    for year in years:
        rows = selected.loc[selected["year"] == year].set_index("class_value")
        output[f"{year} area (km²)"] = rows["area_km2"].reindex(output.index, fill_value=0)
        output[f"{year} share (%)"] = rows["class_percentage"].reindex(output.index, fill_value=0)
    if len(years) == 2:
        output[f"{years[0]}–{years[1]} change (km²)"] = output[f"{years[1]} area (km²)"] - output[f"{years[0]} area (km²)"]
    return output.reset_index(drop=True)


def build_comparison_details(
    table: pd.DataFrame,
    classes: Mapping[int, DynamicWorldClass],
    years: Sequence[int],
) -> str:
    """Render the selected-year table, calculation notes, and full-precision CSV."""
    order = [value for value in (6, 1, 5, 4, 7, 0, 2, 3) if value in classes]
    if 8 in classes and table.loc[table["class_value"] == 8, "area_km2"].gt(0).any():
        order.append(8)
    download = build_download_table(table, classes, years)
    download.index = sorted(classes)
    download = download.loc[order].copy()
    download["Class"] = [
        "Shrub & scrub" if classes[value].name.lower() == "shrub and scrub"
        else classes[value].name.capitalize()
        for value in order
    ]
    headers = {"Class": "Land-cover class"}
    for year in years:
        headers[f"{year} area (km²)"] = f"{year} · km²"
        headers[f"{year} share (%)"] = f"{year} · %"
    if len(years) == 2:
        headers[f"{years[0]}–{years[1]} change (km²)"] = f"{years[0]}–{years[1]} · km² change"
    download = download.rename(columns=headers)
    table_header = "".join(f'<th scope="col">{escape(column)}</th>' for column in download.columns)
    table_rows = []
    for values in download.itertuples(index=False, name=None):
        cells = [f"<td>{escape(values[0])}</td>"]
        for column, value in zip(download.columns[1:], values[1:], strict=True):
            if column.endswith("km² change"):
                formatted = ("−" if value < 0 else "+") + f"{abs(value):,.2f}"
            else:
                formatted = f"{value:,.1f}" if column.endswith("· %") else f"{value:,.2f}"
            cells.append(f"<td>{formatted}</td>")
        table_rows.append("<tr>" + "".join(cells) + "</tr>")
    encoded_csv = base64.b64encode(download.to_csv(index=False).encode("utf-8")).decode("ascii")
    filename = escape(f"class-areas-{'-'.join(map(str, years))}.csv", quote=True)
    comparison = len(years) == 2
    table_scope = "comparison" if comparison else "selected-year"
    download_scope = "selected comparison" if comparison else "selected-year areas"
    return (
        '<details class="lulc-data-details">'
        f'<summary>Inspect the {table_scope} table and calculation notes</summary>'
        '<div class="lulc-details-body">'
        f'<table><thead><tr>{table_header}</tr></thead><tbody>{"".join(table_rows)}</tbody></table>'
        '<p class="lulc-source-note">Local Dynamic World study rasters; nearest-neighbour '
        'reprojection to UTM 31N. Transition areas use pixels valid in both years. '
        'Area shares use valid mapped pixels in each selected year.</p>'
        f'<a class="lulc-download-link" href="data:text/csv;charset=utf-8;base64,{encoded_csv}" '
        f'download="{filename}">Download {download_scope} (CSV) ↓</a>'
        '</div></details>'
    )


def describe_composition(
    table: pd.DataFrame,
    classes: Mapping[int, DynamicWorldClass],
    years: Sequence[int],
) -> tuple[str, str]:
    """Use the wireframe narrative for selected observations and study-wide context."""
    _selected_rows(table, years)

    def value(year: int, class_id: int, measurement: str = "area_km2") -> float:
        rows = table.loc[(table["year"] == year) & (table["class_value"] == class_id)]
        return float(rows[measurement].iloc[0]) if not rows.empty else 0.0

    def area(year: int, class_id: int) -> str:
        return f"{value(year, class_id):,.2f}"

    def share(year: int, class_id: int) -> str:
        return f"{value(year, class_id, 'class_percentage'):,.1f}"

    def change(delta: float, up: str = "increased", down: str = "decreased") -> str:
        return f"{up if delta >= 0 else down} by {abs(delta):,.2f} km²"

    comparing = len(years) == 2
    available_years = sorted(table["year"].unique())
    first, last = (years[0], years[1]) if comparing else (available_years[0], available_years[-1])
    built_change = value(last, 6) - value(first, 6)
    tree_change = value(last, 1) - value(first, 1)
    shrub_change = value(last, 5) - value(first, 5)
    if comparing:
        first_text = (
            f"Between {first} and {last}, built area {change(built_change, 'expanded', 'contracted')}, "
            f"moving from {area(first, 6)} km² ({share(first, 6)}%) to "
            f"{area(last, 6)} km² ({share(last, 6)}%). Over the same interval, "
            f"tree cover {change(tree_change)}, from {area(first, 1)} km² to {area(last, 1)} km²."
        )
        # Keep the wireframe's class order when equally large classes are present.
        class_order = [class_id for class_id in (6, 1, 5, 4, 7, 0, 2, 3) if class_id in classes]
        start_class = max(class_order, key=lambda class_id: value(first, class_id))
        end_class = max(class_order, key=lambda class_id: value(last, class_id))

        def class_name(class_id: int) -> str:
            return "shrub & scrub" if class_id == 5 else classes[class_id].name.lower()

        dominance = (
            f"The largest mapped class at both endpoints was {class_name(end_class)}."
            if start_class == end_class else
            f"The largest mapped class shifted from {class_name(start_class)} in {first} "
            f"to {class_name(end_class)} in {last}."
        )
        second_text = (
            f"Shrub and scrub {change(shrub_change)}, from {area(first, 5)} km² to "
            f"{area(last, 5)} km², accounting for {share(last, 5)}% of the mapped area by {last}. "
            f"{dominance}"
        )
    else:
        year = years[0]
        first_text = (
            f"In {year}, built area occupied {area(year, 6)} km² "
            f"({share(year, 6)}% of the mapped area), while tree cover occupied "
            f"{area(year, 1)} km² ({share(year, 1)}%). Shrub and scrub accounted for "
            f"a further {area(year, 5)} km² ({share(year, 5)}%)."
        )
        second_text = (
            f"Across the full {first}–{last} study period, built area {change(built_change)} "
            f"and tree cover {change(tree_change)}. Shrub and scrub {change(shrub_change)}, "
            f"reaching {area(last, 5)} km² in {last}. This study-wide context complements "
            "the selected-year snapshot above."
        )
    return first_text, second_text
