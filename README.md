# Landshift

Landshift is a Python project that measures how land cover has changed in a study area near Benin City, Nigeria, using Dynamic World data for 2016, 2020 and 2025. The results, including the maps, the class areas and the transitions between classes, can be explored in a Streamlit application.

## Purpose

This project studies how land cover has changed in Uteh, Iwogban and the surrounding communities, an area the author has known closely for over a decade. Landshift records that change with a repeatable spatial method and does not assume that urbanisation is behind every change it finds.

## Study area

| Item | Value |
| --- | --- |
| Location | Uteh, Iwogban and nearby communities, Benin City, Edo State, Nigeria |
| Area | 57.64 km² |
| Landscape | Peri-urban |
| Observation years | 2016, 2020, 2025 (January–February) |
| Spatial resolution | 10 m |
| Projection for area calculation | WGS 84 / UTM zone 31N (EPSG:32631) |

The study area boundary is a custom polygon.
The author drew this polygon on a map of the Umagbae South ward in Edo State.

## Data

The project uses these data sources:

| Data | Source | Location in the repository |
| --- | --- | --- |
| Land cover GeoTIFF files (Dynamic World V1, made from Sentinel-2 imagery) | [Dynamic World](https://dynamicworld.app) | `src/landshift/data/raw/custom_aoi_LULC/` |
| Google Earth Engine script that exports the GeoTIFF files | [Earth Engine script](https://code.earthengine.google.com/ce4354f43bb0776d1be7e5984d8a7b79) | Not in the repository |
| Nigeria ward boundaries (GRID3 Nigeria Operational Wards) | [GRID3 NGA - Operational Wards v4.0](https://data.grid3.org/datasets/GRID3::grid3-nga-operational-wards-v4-0/about) | `src/landshift/data/raw/nigeria_wards_data/` |
| Study area polygon (GeoJSON) | Drawn by the author | `src/landshift/data/raw/custom_aoi_geojson/` |
| Study area polygon (shapefile) | Made from the GeoJSON file | `src/landshift/data/processed/custom_aoi_shapefile/` |

Each GeoTIFF file has one band.
Each pixel value is a Dynamic World class:

| Value | Class |
| --- | --- |
| 0 | Water |
| 1 | Trees |
| 2 | Grass |
| 3 | Flooded vegetation |
| 4 | Crops |
| 5 | Shrub and scrub |
| 6 | Built area |
| 7 | Bare ground |
| 8 | Snow and ice |

Each GeoTIFF file name must contain one year, for example `lulc_2016_jan_feb.tif`.

## Data attribution

The project uses data from other providers. Each provider keeps its own license.

### Dynamic World V1

- License: [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/).
- Source: [Earth Engine catalog, GOOGLE/DYNAMICWORLD/V1](https://developers.google.com/earth-engine/datasets/catalog/GOOGLE_DYNAMICWORLD_V1).
- Required attribution:

  > This dataset is produced for the Dynamic World Project by Google in partnership with National Geographic Society and the World Resources Institute.

- The land cover data comes from Sentinel-2 imagery. The catalog gives this notice:

  > Contains modified Copernicus Sentinel data [2015-present].

- Citation:

  > Brown, C.F., Brumby, S.P., Guzder-Williams, B. et al. Dynamic World, Near real-time global 10 m land use land cover mapping. Sci Data 9, 251 (2022). https://doi.org/10.1038/s41597-022-01307-4

### GRID3 Nigeria Operational Wards

- The project uses the ward boundaries from GRID3.
- The file in `src/landshift/data/raw/nigeria_wards_data/` comes from the earlier version 1.0 release. Version 4.0 is the current release.
- License for version 4.0: [Creative Commons Attribution-ShareAlike 4.0 International (CC BY-SA 4.0)](https://creativecommons.org/licenses/by-sa/4.0/).
- Copyright 2026. The Trustees of Columbia University in the City of New York.
- Citation (as given by the provider):

  > Center for Integrated Earth System Information (CIESIN), Columbia University 2026. GRID3 NGA - Operational Wards v4.0. New York: Columbia University. https://doi.org/10.7916/3v3g-f998. Accessed [DAY MONTH YEAR].

### Basemap tiles

- The application and the notebooks show OpenStreetMap tiles under the maps.
- The OpenStreetMap data uses the [Open Database License (ODbL)](https://opendatacommons.org/licenses/odbl/).
- Required attribution: © OpenStreetMap contributors. Refer to the [OpenStreetMap copyright page](https://www.openstreetmap.org/copyright).
- The tile use must obey the [OpenStreetMap tile usage policy](https://operations.osmfoundation.org/policies/tiles/).

## Analyses

The `services` folder contains the analysis functions:

- **Study area preparation** (`services/aoi.py`): selects a ward by ward name and state name. It also repairs the study area polygon and combines it into one feature.
- **Class area** (`services/class_area.py`): counts the pixels in each class. It calculates the area (km²) and the percentage of each class for each year. It also calculates the percentage change between years.
- **Transitions** (`services/transition.py`): compares two years pixel by pixel. It makes a transition matrix in pixels, km² and percent. It also calculates the persistence, gain and loss for each class.
- **Raster preparation** (`services/raster.py`): reprojects each raster with nearest-neighbour resampling. This method keeps the class values. The area calculation uses EPSG:32631. The map overlay uses EPSG:3857.

## Application pages

The Streamlit application has three pages:

1. **Home**: shows the project purpose, the study area facts, the method, the data sources and three key findings.
2. **Area Analysis**: shows the land cover map for one year, or two maps side by side for two years. It also shows the area or the percentage of each class, and a text summary of the change.
3. **Transition Analysis**: shows the transitions between two years. You select the period. The page shows the largest conversions and the full transition matrix. You can download the matrix as a CSV file.

## Notebooks

The `src/landshift/analysis` folder contains Jupyter notebooks. The notebooks show the steps of the analysis:

1. `01_clip_and_visualise_area_of_interest.ipynb`: loads the ward boundaries, shows the Umagbae South ward and saves the study area as a shapefile.
2. `02_inspect_dynamic_world.ipynb`: reads the GeoTIFF metadata, counts the pixels in each class and shows the rasters on a map.
3. `03_class_area_analysis.ipynb`: calculates the class areas, the percentage change and the transitions between two years.

## Project structure

```text
.
├── pyproject.toml
├── uv.lock
├── src/
│   └── landshift/
│       ├── app.py              # Streamlit entry point
│       ├── .streamlit/         # Streamlit configuration
│       ├── analysis/           # Jupyter notebooks
│       ├── config/             # config.py and config.yaml
│       ├── data/               # raw and processed data
│       ├── data_access/        # functions that read raster and vector files
│       ├── services/           # analysis functions
│       ├── ui/                 # pages, components and CSS
│       └── utils/
└── tests/
```

## Requirements

- Python 3.13 or later
- [uv](https://docs.astral.sh/uv/)

## Installation

1. Clone the repository.
2. Go to the repository root folder.
3. Install the dependencies:

   ```bash
   uv sync
   ```

## Start the application

1. Go to the application folder:

   ```bash
   cd src/landshift
   ```

2. Start the application:

   ```bash
   uv run streamlit run app.py
   ```

3. Open the URL that Streamlit shows in the terminal.

Start the application from the `src/landshift` folder. Streamlit reads the `.streamlit/config.toml` file from the current folder.

## Run the tests

1. Go to the repository root folder.
2. Run the tests:

   ```bash
   uv run pytest
   ```

## Configuration

- `src/landshift/config/config.yaml` contains the application name, the Dynamic World classes and colours, and the data paths.
- `src/landshift/config/config.py` reads `config.yaml` and validates it with OmegaConf.
- `src/landshift/.streamlit/config.toml` contains the Streamlit server and theme settings.

## License

This project uses the Unlicense. Refer to the `LICENSE` file.
The Unlicense applies only to the project code.
The data sources keep their own licenses. Refer to the [Data attribution](#data-attribution) section.
