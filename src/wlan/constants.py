
from os import path
from dataclasses import dataclass

from wlan.utils import PathUtils

BUNDLED_PATH = PathUtils.get_bundled_path()


@dataclass(frozen=True)
class AppConstants:
    APP_ID = "WLAN Monitor"
    ICON_FILE = "favicon.ico"
    ICON_PATH = path.join(BUNDLED_PATH, ICON_FILE)
