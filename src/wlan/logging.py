import logging
import os

from wlan.managers import ConfigManager
from wlan.utils import PathUtils

BASE_PATH = PathUtils.get_base_path()

logger = logging.getLogger(__name__)

logging_file = os.path.join(BASE_PATH, "running.log")
logging_level = int(ConfigManager.get("main.logging_level", 20))
loggin_format = '%(asctime)s - %(levelname)s - %(message)s'

logging.basicConfig(
    filename=logging_file,
    level=logging_level,
    format=loggin_format
)
