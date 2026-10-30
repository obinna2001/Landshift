"""Prepare selected-period transitions, presentation, and full-precision downloads."""

import base64
from collections.abc import Collection, Mapping
from html import escape
import math
from pathlib import Path
import re

import pandas as pd

from land_cover_change.config.config import DynamicWorldClass
from land_cover_change.services.raster import (
    calculate_pixel_area,
    prepare_analysis_raster,
    validate_raster_alignment,
)
from land_cover_change.services.transition import (
    calculate_transition_matrix,
    summarize_transitions,
    transition_areas,
)


_ACTIVE_IDS = (6, 1, 5, 4, 7, 0, 2, 3)
_PREVIEW_IDS = (1, 6, 5, 4, 7)


def build_transition_matrix(
    earlier_path: str | Path,
    later_path: str | Path,
    classes: Collection[int],
) -> pd.DataFrame:
    """Measure earlier-to-later class areas on the common valid analysis grid."""
    validate_raster_alignment([earlier_path, later_path])
    earlier = prepare_analysis_raster(earlier_path)
    later = prepare_analysis_raster(later_path)
    if (
        earlier.crs != later.crs
        or earlier.transform != later.transform
        or earlier.data.shape != later.data.shape
    ):
        raise ValueError("The prepared study rasters must share the same analysis grid")
    counts = calculate_transition_matrix(earlier.data, later.data, classes)
    return transition_areas(counts, calculate_pixel_area(earlier.transform))


def transition_matrix_csv(matrix: pd.DataFrame, class_names: Mapping[int, str]) -> str:
    """Label the complete area matrix without rounding any exported measurements."""
    return matrix.rename(index=class_names, columns=class_names).to_csv(
        index_label="Earlier class / Later class"
    )


def build_transition_csv(
    earlier_path: str | Path,
    later_path: str | Path,
    class_names: Mapping[int, str],
) -> str:
    """Export km² from earlier classes to later classes on the common valid grid."""
    matrix = build_transition_matrix(earlier_path, later_path, tuple(class_names))
    return transition_matrix_csv(matrix, class_names)


def build_transition_content(
    matrix: pd.DataFrame,
    classes: Mapping[int, DynamicWorldClass],
    years: tuple[int, int],
) -> str:
    """Render the wireframe analysis using a single selected-period area matrix."""
    # The service validates finite, nonnegative values and matching matrix axes.
    summary = summarize_transitions(matrix)
    if set(matrix.index).difference(classes):
        raise ValueError("The transition matrix contains classes absent from the registry")
    for definition in classes.values():
        if not re.fullmatch(r"#[0-9a-fA-F]{6}", definition.colour):
            raise ValueError("Transition class colours must be six-digit hexadecimal values")
    matrix = matrix.loc[matrix.index, matrix.index]
    period = f"{years[0]}–{years[1]}"

    def name(class_id: int) -> str:
        if class_id == 5:
            return "Shrub & scrub"
        if class_id == 8:
            return "Snow & ice"
        return classes[class_id].name.capitalize()

    def pair_label(earlier: int, later: int) -> str:
        return f"{name(earlier)} → {name(later)}"

    def area(earlier: int, later: int) -> float:
        return float(matrix.at[earlier, later])         #type: ignore

    total = float(matrix.to_numpy().sum())
    retained = float(summary["persistence_km2"].sum())
    changed = float(summary["loss_km2"].sum())
    conversions = sorted(
        ((area(earlier, later), earlier, later)                 #type: ignore
         for earlier in matrix.index for later in matrix.columns
         if earlier != later and area(earlier, later) > 0),         #type: ignore
        key=lambda item: (-item[0], item[1], item[2]),
    )
    largest = conversions[0] if conversions else None

    def stat(key: str, label: str, value: float, note: str) -> str:
        return (
            f'<div class="stat" data-stat="{key}">'
            f'<div class="stat-label">{label}</div>'
            f'<div class="stat-number" data-area-km2="{value:.17g}">{value:,.2f}'
            '<small> km²</small></div>'
            f'<div class="stat-note">{escape(note)}</div></div>'
        )

    def footprint_note(value: float) -> str:
        return f"{value / total * 100 if total else 0:.1f}% of the common valid footprint"

    stats = (
        '<div class="stat-strip">'
        + stat("changed", "Mapped class changed", changed, footprint_note(changed))
        + stat("retained", "Mapped class retained", retained, footprint_note(retained))
        + stat(
            "largest", "Largest conversion", largest[0] if largest else 0,
            pair_label(largest[1], largest[2]) if largest else "No mapped conversions",         #type: ignore
        )
        + '</div>'
    )
    bars = []
    domain = largest[0] * 1.12 if largest else 1
    for value, earlier, later in conversions[:5]:
        bars.append(
            f'<div class="bar-row" data-from-class="{earlier}" data-to-class="{later}" '
            f'data-area-km2="{value:.17g}">'
            f'<span class="bar-label">{escape(pair_label(earlier, later))}</span>'          #type: ignore
            '<div class="bar-track">'
            f'<div class="bar-fill" style="width:{value / domain * 100:.12g}%;'
            f'background:{classes[later].colour}" title="{value:,.2f} km²"></div></div>'        #type: ignore
            f'<span class="bar-number">{value:,.2f}</span></div>'
        )
    empty_note = (
        '<p class="chart-description">No mapped class conversions occurred during this period.</p>'
        if not largest else ''
    )
    conversion_bars = (
        f'<div class="bar-list transition-bars">{"".join(bars)}</div>{empty_note}'
        '<p class="chart-caption">Five largest conversions · km². Colour identifies the '
        'destination class. Pixels that retained their class are excluded from this ranking.</p>'
    )
    if largest:
        value, earlier, later = largest
        story = (
            '<div class="conversion-story">'
            f'<h3>{escape(pair_label(earlier, later))} was the largest mapped conversion</h3>'         #type: ignore
            f'<p>This pair accounts for {value:,.2f} km² during {period}. It describes a change '
            'in mapped class; it does not establish the cause.</p></div>'
        )
    else:
        story = (
            '<div class="conversion-story"><h3>No mapped class conversions were observed</h3>'
            f'<p>No mapped class conversions were observed during {period}.</p></div>'
        )

    preview_ids = [class_id for class_id in _PREVIEW_IDS if class_id in matrix.index]
    maximum = float(matrix.to_numpy().max())
    matrix_cells = ['<div class="matrix-label top">From ↓ / To →</div>']
    matrix_cells.extend(
        f'<div class="matrix-label top">{escape(name(class_id))}</div>'
        for class_id in preview_ids
    )
    for earlier in preview_ids:
        matrix_cells.append(
            '<div class="matrix-label">'
            f'<i class="swatch" style="background:{classes[earlier].colour}"></i>'
            f'&nbsp; {escape(name(earlier))}</div>'
        )
        for later in preview_ids:
            value = area(earlier, later)
            intensity = math.sqrt(value / maximum) if maximum else 0
            rgb = tuple(math.floor(component - spread * intensity + .5)
                        for component, spread in ((240, 183), (244, 119), (235, 162)))
            foreground = "#fff" if intensity > .65 else "#3f4b46"
            label = "—" if value < .005 else f"{value:,.{2 if value < 1 else 1}f}"
            tooltip = escape(f"{pair_label(earlier, later)}: {value:,.2f} km²", quote=True)
            matrix_cells.append(
                f'<div class="matrix-cell" data-from-class="{earlier}" data-to-class="{later}" '
                f'data-area-km2="{value:.17g}" style="background:rgb({rgb[0]},{rgb[1]},{rgb[2]});'
                f'color:{foreground}" title="{tooltip}">{label}</div>'
            )
    matrix_preview = (
        '<p class="matrix-axis">Rows: earlier class · Columns: later class</p>'
        '<div class="matrix-wrap"><div class="matrix" '
        f'style="grid-template-columns:74px repeat({len(preview_ids)},minmax(34px,1fr))">'
        + ''.join(matrix_cells)
        + '</div></div><div class="matrix-key"><span>Smaller area</span>'
        '<i class="gradient-key"></i><span>Larger area</span></div>'
        '<p class="chart-note">Five classes shown in this preview. Diagonal cells show '
        'persistence. Off-diagonal cells show conversions.</p>'
    )

    active_ids = [class_id for class_id in _ACTIVE_IDS if class_id in matrix.index]
    if 8 in matrix.index and (matrix.loc[8].sum() > 0 or matrix[8].sum() > 0):      #type: ignore
        active_ids.append(8)
    headers = ''.join(f'<th scope="col">{escape(name(class_id))}</th>' for class_id in active_ids)
    rows = ''.join(
        f'<tr data-from-class="{earlier}"><th scope="row">{escape(name(earlier))}</th>'
        + ''.join(f'<td data-to-class="{later}">{area(earlier, later):,.2f}</td>' for later in active_ids)
        + '</tr>'
        for earlier in active_ids
    )
    class_names = {value: definition.name.capitalize() for value, definition in classes.items()}
    encoded_csv = base64.b64encode(transition_matrix_csv(matrix, class_names).encode()).decode()
    details = (
        '<details class="data-details"><summary>Inspect the complete transition matrix and notes</summary>'
        '<div class="details-body"><table><thead><tr><th scope="col">From ↓ / To →</th>'
        f'{headers}</tr></thead><tbody>{rows}</tbody></table>'
        '<p class="source-note">Local Dynamic World study rasters; nearest-neighbour '
        'reprojection to UTM 31N. Transition areas use pixels valid in both years. '
        'Comparisons describe classes at the two endpoints, rather than a continuous '
        'record of events in between.</p>'
        f'<a href="data:text/csv;charset=utf-8;base64,{encoded_csv}" '
        f'download="study-transitions-{years[0]}-{years[1]}.csv" class="download-link">'
        'Download transition matrix (CSV) ↓</a></div></details>'
    )
    return (
        f'<div class="transition-analysis-content" data-period="{period}">{stats}'
        '<div class="transition-grid"><section class="chart-panel" aria-labelledby="transition-conversions-heading">'
        '<h2 class="chart-heading" id="transition-conversions-heading">Where the largest conversions occurred</h2>'
        f'<p class="chart-description">Changes between mapped classes · {period}</p>'
        f'{conversion_bars}{story}</section>'
        '<section class="chart-panel" aria-labelledby="transition-matrix-heading">'
        '<h2 class="chart-heading" id="transition-matrix-heading">Read the connections between classes</h2>'
        '<p class="chart-description">Transition matrix · area in km²</p>'
        f'{matrix_preview}</section></div>{details}</div>'
    )
