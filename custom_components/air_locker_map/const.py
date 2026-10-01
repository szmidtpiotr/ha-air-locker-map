"""Stałe integracji Air Locker Map."""

DOMAIN = "air_locker_map"

DEFAULT_URL = "https://air-locker-map.studio-colorbox.com"
ATTRIBUTION = "Dane: czujniki w paczkomatach InPost (nieoficjalne), air-locker-map"

CONF_MODE = "mode"
CONF_CODE = "code"
CONF_INCLUDE_SUSPECT = "include_suspect"
CONF_SCAN_MINUTES = "scan_minutes"

MODE_HOME = "home"        # najbliższy działający czujnik do domu (współrzędne z HA)
MODE_LOCKER = "locker"    # najbliższy czujnik do wskazanego paczkomatu (także bez czujnika)
MODE_SENSOR = "sensor"    # konkretny czujnik, bez zastępowania

DEFAULT_SCAN_MINUTES = 15
MIN_SCAN_MINUTES = 10

CONF_THRESHOLD = "threshold"   # próg PM2.5 dla czujnika „Przekroczenie normy”
DEFAULT_THRESHOLD = 35          # granica dobry → umiarkowany (indeks GIOŚ)
THRESHOLD_OPTIONS = [13, 35, 55, 75]
RESOLVE_RATIO = 0.8             # wyłączenie poniżej 80% progu — histereza jak na serwerze
