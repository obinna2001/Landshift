from functools import partial
from itertools import combinations
import logging
from pathlib import Path

import pandas as pd
from rasterio.errors import RasterioIOError
import streamlit as st

from landshift.ui.components.area_analysis import discover_year_paths
from landshift.ui.components.transition_analysis import (
    build_transition_content,
    build_transition_matrix,
    transition_matrix_csv,
)
from landshift.config.config import resolved_config


logger = logging.getLogger(__name__)


@st.cache_data(show_spinner=False)
def load_transition_matrix(
    earlier_file: tuple[str, int, int],
    later_file: tuple[str, int, int],
    class_values: tuple[int, ...],
) -> pd.DataFrame:
    """Share selected-period measurements between the figures and CSV downloads."""
    return build_transition_matrix(earlier_file[0], later_file[0], class_values)


@st.cache_data(show_spinner=False)
def load_transition_csv(
    earlier_file: tuple[str, int, int],
    later_file: tuple[str, int, int],
    registry: tuple[tuple[int, str], ...],
) -> str:
    """Cache downloads by the selected files, their revisions, and class labels."""
    matrix = load_transition_matrix(earlier_file, later_file, tuple(value for value, _ in registry))
    return transition_matrix_csv(matrix, dict(registry))


def render_transition_analysis() -> None:
    """Select a period and render the figures, full matrix, and matching downloads."""
    try:
        paths = discover_year_paths(resolved_config.dataset.raw_dataset.aoi_lulc)
    except (OSError, ValueError, RasterioIOError):
        st.info("Study rasters could not be loaded. Check the configured land-cover dataset.")
        return
    if len(paths) < 2:
        st.info("At least two study years are needed for transition analysis.")
        return
    pairs = sorted(combinations(paths, 2), key=lambda pair: (pair[1] - pair[0], pair[0]))
    periods = {f"{earlier}–{later}": (earlier, later) for earlier, later in pairs}
    if "transition-period" in st.session_state and st.session_state["transition-period"] not in periods:
        st.session_state["transition-period"] = next(reversed(periods))
    with st.container(
        key="transition-toolbar", horizontal=True,
        horizontal_alignment="distribute", vertical_alignment="center", gap=None,
    ):
        with st.container(
            key="transition-period-control", horizontal=True,
            vertical_alignment="center", gap=None, width="content",
        ):
            st.html('<span class="transition-period-label">Period</span>', width="content")
            selected = st.segmented_control(
                "Period", tuple(periods), default=next(reversed(periods)),
                required=True, key="transition-period",
                label_visibility="collapsed", width="content",
            )
        earlier, later = periods[selected]

        def signature(path: Path) -> tuple[str, int, int]:
            metadata = path.stat()
            return str(path), metadata.st_mtime_ns, metadata.st_size

        registry = tuple(
            (value, definition.name.capitalize())
            for value, definition in resolved_config.dynamic_world.classes.items()
        )
        try:
            earlier_file, later_file = signature(paths[earlier]), signature(paths[later])
        except OSError:
            logger.exception("The selected transition rasters could not be accessed")
            st.error("The selected transition period could not be prepared. Check the selected study rasters.")
            return
        st.download_button(
            "Download matrix ↓",
            data=partial(load_transition_csv, earlier_file, later_file, registry),
            file_name=f"study-transitions-{earlier}-{later}.csv", mime="text/csv",
            key="transition-download", on_click="ignore", type="tertiary", width="content",
        )
    try:
        matrix = load_transition_matrix(earlier_file, later_file, tuple(value for value, _ in registry))
        content = build_transition_content(matrix, resolved_config.dynamic_world.classes, (earlier, later))
    except (OSError, ValueError, RasterioIOError):
        logger.exception("The selected transition period could not be prepared")
        st.error("The selected transition period could not be prepared. Check the selected study rasters.")
        return
    st.markdown(content, unsafe_allow_html=True)
    with st.container(
        key="transition-next-perspective", horizontal=True,
        horizontal_alignment="distribute", vertical_alignment="center", gap=None,
    ):
        st.html('<span class="transition-return-label">Return to the spatial picture</span>', width="content")
        st.page_link(
            "ui/views/area_analysis.py", label="Explore the land-cover map →", width="content",
        )


with st.container(key="title-section"):
    with st.container(key="title-content"):
        st.markdown(
            """
            <p class="hero-eyebrow">
                ~ Transition analysis
            </p>

            <h1 class="hero-title">
                Tracing the changes between land-cover classess    
            </h1>

            <p class="hero-lead">
                Look beyond the totals to see what retained its mapped class, what changed,
                and which conversions account for the largest area
            </p>
            """,
            unsafe_allow_html=True,
        )


with st.container(key="transition-workspace"):
    render_transition_analysis()
