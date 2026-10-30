"""Verify direct Streamlit startup without pytest's source-path configuration."""

import os
from pathlib import Path
import subprocess
import sys

import numpy as np


APP = Path(__file__).resolve().parents[1] / "src/landshift/app.py"


def test_app_starts_and_opens_lulc_map_without_pythonpath(tmp_path, raster_factory):
    for year in (2016, 2020, 2025):
        raster_factory(f"lulc_{year}.tif", np.array([[1, 1], [1, 6]], dtype="uint8"))
    working_directory = tmp_path / "unrelated-directory"
    working_directory.mkdir()
    environment = os.environ.copy()
    environment.pop("PYTHONPATH", None)
    environment.pop("PYTHONHOME", None)
    environment.update({
        "PYTHONDONTWRITEBYTECODE": "1",
        "GDAL_PAM_ENABLED": "NO",
        "MPLCONFIGDIR": str(tmp_path / "matplotlib"),
    })
    script = r'''
from pathlib import Path
import sys
from streamlit.testing.v1 import AppTest

app_path = Path(sys.argv[1])
assert str(app_path.parents[1]) not in sys.path
app = AppTest.from_file(str(app_path), default_timeout=30).run()
assert not app.exception, [error.message for error in app.exception]
from landshift.config.config import resolved_config
resolved_config.dataset.raw_dataset.aoi_lulc = sys.argv[2]
app.switch_page("ui/views/area_analysis.py").run()
assert not app.exception, [error.message for error in app.exception]
assert len(app.get("iframe")) == 1
assert app.get("iframe")[0].proto.srcdoc.count("L.map(") == 2
app.switch_page("ui/views/transition_analysis.py").run()
assert not app.exception, [error.message for error in app.exception]
print("Startup and LULC navigation succeeded")
'''
    completed = subprocess.run(
        [sys.executable, "-B", "-c", script, str(APP), str(tmp_path)],
        cwd=working_directory,
        env=environment,
        capture_output=True,
        text=True,
        timeout=60,
    )
    assert completed.returncode == 0, completed.stdout + completed.stderr
    assert "Startup and LULC navigation succeeded" in completed.stdout
