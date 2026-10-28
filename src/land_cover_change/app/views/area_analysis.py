"""Explore annual land-cover maps and their linked class-area analysis."""
from html import escape
from inspect import getfile
from pathlib import Path

import pandas as pd
from rasterio.errors import RasterioIOError
import streamlit as st

from land_cover_change.app.components.area_analysis import (
    build_class_chart,
    build_comparison_details,
    build_explorer_map,
    build_explorer_legend,
    describe_composition,
    discover_year_paths,
)
from land_cover_change.config.config import DynamicWorldClass, resolved_config
from land_cover_change.services.class_area import build_class_area_table
from land_cover_change.services.raster import RasterMapOverlay, prepare_map_overlay


@st.cache_data(show_spinner=False)
def load_areas(
    files: tuple[tuple[str, int, int], ...],
    class_values: tuple[int, ...],
) -> pd.DataFrame:
    """Cache area measurements, invalidating when input files change."""
    return build_class_area_table(
        [path for path, _, _ in files],
        class_values,
    )


@st.cache_data(show_spinner=False)
def load_overlay(
    path: str,
    modified: int,
    size: int,
    palette: tuple[tuple[int, str], ...],
) -> RasterMapOverlay:
    """Cache the Mercator overlay using its file and palette signature."""
    return prepare_map_overlay(path, dict(palette))


@st.cache_data(show_spinner=False)
def load_map(
    files: tuple[tuple[int, str, int, int], ...],
    registry: tuple[tuple[int, str, str], ...],
    renderer_revision: int,
) -> tuple[str, int]:
    """Keep the same iframe document when unrelated analysis controls change."""
    classes = {
        value: DynamicWorldClass(name=name, colour=colour)
        for value, name, colour in registry
    }
    palette = tuple((value, colour) for value, _, colour in registry)
    overlays = {
        year: load_overlay(path, modified, size, palette)
        for year, path, modified, size in files
    }
    return build_explorer_map(overlays, classes)


def render_explorer() -> None:
    classes = resolved_config.dynamic_world.classes
    try:
        paths = discover_year_paths(resolved_config.dataset.raw_dataset.aoi_lulc)
        signatures = tuple(
            (str(path), path.stat().st_mtime_ns, path.stat().st_size)
            for path in paths.values()
        )
        areas = load_areas(signatures, tuple(classes))
    except (OSError, ValueError, RasterioIOError):
        st.error("The study rasters could not be loaded. Check the configured land-cover dataset.")
        return

    years = tuple(paths)
    legend_classes = dict(classes)
    if not areas.loc[areas["class_value"] == 8, "area_km2"].gt(0).any():
        legend_classes.pop(8, None)
    with st.container(key="lulc-workspace"):
        with st.container(key="lulc-controls"):
            mode_col, first_col, last_col, reset_col = st.columns(
                [1.2, 1, 1, 1.25], vertical_alignment="bottom"
            )
            with mode_col:
                mode = st.selectbox(
                    "View", ("Single year", "Compare years"),
                    index=1 if len(years) > 1 else 0, key="lulc-view-mode",
                )
            comparing = mode == "Compare years" and len(years) > 1
            if comparing:
                with first_col:
                    earlier = st.selectbox("Earlier year", years[:-1], key="lulc-earlier-year")
                later_options = tuple(year for year in years if year > earlier)
                if st.session_state.get("lulc-later-year") not in later_options:
                    st.session_state["lulc-later-year"] = later_options[-1]
                with last_col:
                    later = st.selectbox("Later year", later_options, key="lulc-later-year")
                selected = (earlier, later)
            else:
                with first_col:
                    year = st.selectbox("Study year", years, index=len(years) - 1, key="lulc-study-year")
                selected = (year,)
            with reset_col:
                if st.button("Reset maps extent" if comparing else "Reset map extent", width="stretch"):
                    st.session_state["lulc-extent-revision"] = st.session_state.get("lulc-extent-revision", 0) + 1

        registry = tuple(
            (value, definition.name, definition.colour)
            for value, definition in classes.items()
        )
        try:
            with st.spinner("Preparing the selected maps…"):
                selected_files = tuple(
                    (year, str(paths[year]), paths[year].stat().st_mtime_ns,
                     paths[year].stat().st_size)
                    for year in selected
                )
                map_html, map_height = load_map(
                    selected_files, registry,
                    Path(getfile(build_explorer_map)).stat().st_mtime_ns,
                )
        except (OSError, ValueError, RasterioIOError):
            st.error("The selected map could not be prepared. Check the selected study rasters.")
            return
        revision = st.session_state.get("lulc-extent-revision", 0)
        st.iframe(f"{map_html}\n<!-- extent-revision:{revision} -->", height=map_height)
        st.html(
            '<div class="lulc-map-caption"><span>Dynamic World V1 · January–February observations</span></div>'
        )
        st.html(build_explorer_legend(legend_classes))

        with st.container(key="lulc-analysis"):
            with st.container(key="lulc-analysis-heading"):
                heading_col, unit_col = st.columns([3, 1], vertical_alignment="bottom")
                with heading_col:
                    scope = "Selected comparison" if comparing else "Selected year"
                    description = (
                        f"Class areas in {selected[0]} and {selected[1]}, matching the two maps above."   #type: ignore
                        if comparing else f"Class areas in {selected[0]}, matching the selected map."
                    )
                    st.html(
                        f'<p class="lulc-eyebrow">Area analysis · {scope}</p>'
                        '<h2 class="lulc-section-title">Compare the individual classes</h2>'
                        f'<p class="lulc-section-description">{description}</p>'
                    )
                with unit_col:
                    with st.container(
                        key="lulc-unit-control", horizontal=True,
                        horizontal_alignment="right", vertical_alignment="center", gap=None,
                    ):
                        st.html('<span class="lulc-unit-label">Show</span>', width="content")
                        unit_label = st.segmented_control(
                            "Show", ("Share (%)", "Area (km²)"),
                            default="Share (%)", required=True, key="lulc-area-unit",
                            label_visibility="collapsed", width="content",
                        )
            unit = "share" if unit_label == "Share (%)" else "area"
            st.html(build_class_chart(areas, classes, selected, unit=unit))

            with st.container(key="lulc-interpretation"):
                story_heading, story_copy = st.columns([0.8, 1.5], gap="medium")
                with story_heading:
                    story_scope = (
                        f"Selected comparison · {selected[0]}–{selected[-1]}"
                        if comparing else
                        f"{selected[0]} snapshot · wider context from {min(years)}–{max(years)}"
                    )
                    st.html(
                        '<p class="lulc-eyebrow">Reading the change</p>'
                        '<h2 class="lulc-section-title">How the balance of land cover shifted</h2>'
                        f'<p class="lulc-story-scope">{story_scope}</p>'
                    )
                with story_copy:
                    paragraphs = "".join(
                        f'<p class="lulc-story-copy">{escape(paragraph)}</p>'
                        for paragraph in describe_composition(areas, classes, selected)
                    )
                    st.html(f'<div class="lulc-story-paragraphs">{paragraphs}</div>')

            st.markdown(
                build_comparison_details(areas, classes, selected),
                unsafe_allow_html=True,
            )

        with st.container(
            key="lulc-next-perspective", horizontal=True,
            horizontal_alignment="distribute", vertical_alignment="center", gap=None,
        ):
            st.html('<span class="lulc-next-label">Next perspective</span>', width="content")
            st.page_link(
                "views/transition_analysis.py", label="What changed into what? →", width="content",
            )


with st.container(key="title-section"):
    with st.container(key="title-content"):
        st.markdown(
            """
            <p class="hero-eyebrow">
                ~ Area Analysis
            </p>

            <h1 class="hero-title">
                Explore the landscape across three study years    
            </h1>

            <p class="hero-lead">
                Compare land-cover patterns across Uteh, Iwogban and nearby communities in 2016, 
                2020 and 2025. Explore where built land expanded, tree cover declined and other 
                land-cover classes changed across the study area.
            </p>
            """,
            unsafe_allow_html=True,
        )

render_explorer()
