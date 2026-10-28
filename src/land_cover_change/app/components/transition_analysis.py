"""Prepare selected-period transition downloads from the study rasters."""

from collections.abc import Mapping
from pathlib import Path

from land_cover_change.services.raster import (
    calculate_pixel_area,
    prepare_analysis_raster,
    validate_raster_alignment,
)
from land_cover_change.services.transition import calculate_transition_matrix, transition_areas


def build_transition_csv(
    earlier_path: str | Path,
    later_path: str | Path,
    class_names: Mapping[int, str],
) -> str:
    """Export km² from earlier classes to later classes on the common valid grid."""
    validate_raster_alignment([earlier_path, later_path])
    earlier = prepare_analysis_raster(earlier_path)
    later = prepare_analysis_raster(later_path)
    if (
        earlier.crs != later.crs
        or earlier.transform != later.transform
        or earlier.data.shape != later.data.shape
    ):
        raise ValueError("The prepared study rasters must share the same analysis grid")
    counts = calculate_transition_matrix(earlier.data, later.data, tuple(class_names))
    areas = transition_areas(counts, calculate_pixel_area(earlier.transform))
    areas = areas.rename(index=class_names, columns=class_names)
    return areas.to_csv(index_label="Earlier class / Later class")
