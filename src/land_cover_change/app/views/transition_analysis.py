from functools import partial
from itertools import combinations
from pathlib import Path

from rasterio.errors import RasterioIOError
import streamlit as st

from land_cover_change.app.components.area_analysis import discover_year_paths
from land_cover_change.app.components.transition_analysis import build_transition_csv
from land_cover_change.config.config import resolved_config


@st.cache_data(show_spinner=False)
def load_transition_csv(
    earlier_file: tuple[str, int, int],
    later_file: tuple[str, int, int],
    registry: tuple[tuple[int, str], ...],
) -> str:
    """Cache downloads by the selected files, their revisions, and class labels."""
    return build_transition_csv(earlier_file[0], later_file[0], dict(registry))


def render_period_toolbar() -> None:
    """Select an available comparison period and download its transition matrix."""
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
        st.download_button(
            "Download matrix ↓",
            data=partial(load_transition_csv, signature(paths[earlier]), signature(paths[later]), registry),
            file_name=f"study-transitions-{earlier}-{later}.csv", mime="text/csv",
            key="transition-download", on_click="ignore", type="tertiary", width="content",
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
    render_period_toolbar()
