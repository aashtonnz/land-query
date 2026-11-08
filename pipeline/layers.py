"""The public layers fetched for each block: the chosen council's (councils/, T-86). See SOURCES.md."""
from councils import COUNCIL as _C

ARCGIS = _C.ARCGIS
BUILDINGS_CAPTURE = _C.BUILDINGS_CAPTURE
KC_LIC = getattr(_C, "KC_LIC", None)   # Kāpiti's portal statement, used in its provenance
KC = getattr(_C, "KC", None)
