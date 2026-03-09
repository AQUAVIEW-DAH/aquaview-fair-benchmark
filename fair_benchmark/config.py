"""Configuration: STAC API URL, scoring weights, sample queries."""

import os

STAC_API_URL = os.environ.get(
    "AQUAVIEW_STAC_URL",
    "https://aquaview-sfeos-1025757962819.us-east1.run.app",
)

HTTP_TIMEOUT = float(os.environ.get("AQUAVIEW_FAIR_TIMEOUT", "30"))

# Grading scale: A=4, B=3, C=2, D=1, F=0
GRADE_VALUES = {"A": 4, "B": 3, "C": 2, "D": 1, "F": 0}
GRADE_LABELS = {4: "A", 3: "B", 2: "C", 1: "D", 0: "F"}

# F and A principles weighted 1.5x per GO-FAIR guidance
PRINCIPLE_WEIGHTS = {
    "F1": 1.5, "F2": 1.5, "F3": 1.5, "F4": 1.5,
    "A1": 1.5, "A1.1": 1.5, "A1.2": 1.5, "A2": 1.5,
    "I1": 1.0, "I2": 1.0, "I3": 1.0,
    "R1": 1.0, "R1.1": 1.0, "R1.2": 1.0, "R1.3": 1.0,
}

# Sample queries for catalog probing
SEARCH_QUERIES = [
    {"q": "sea surface temperature", "label": "free-text: sea surface temperature"},
    {"q": "bathymetry", "label": "free-text: bathymetry"},
    {"q": "wave height", "label": "free-text: wave height"},
]

BBOX_QUERIES = [
    {"bbox": "-98,18,-80,31", "label": "spatial: Gulf of Mexico"},
    {"bbox": "-60,30,-10,60", "label": "spatial: North Atlantic"},
]

# Known controlled vocabulary URIs for checking
CF_STANDARD_NAMES_URI = "http://cfconventions.org/Data/cf-standard-names/"
GCMD_KEYWORDS_URI = "https://gcmd.earthdata.nasa.gov/kms/"
