
from os import path
from dataclasses import dataclass

from wlan.utils import PathUtils

BASE_PATH = PathUtils.get_base_path()


@dataclass(frozen=True)
class AppConstants:
    APP_ID = "WLAN Monitor"
    ICON_FILE = "application.ico"
    ICON_PATH = path.join(BASE_PATH, ICON_FILE)
