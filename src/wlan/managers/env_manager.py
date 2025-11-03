import logging
import os
from contextlib import nullcontext
from threading import Lock

from dotenv import load_dotenv

from wlan.descriptors import static_property
from wlan.utils import PathUtils

logger = logging.getLogger(__name__)


class EnvManager:
    __loaded = False
    __env_data = None
    __lock = Lock()

    @static_property
    def loaded(self):
        with self.__lock:
            return self.__loaded

    @staticmethod
    def load_env(file_name=".env", base_path: str = None, override: bool = True, lock=True) -> bool:
        with (EnvManager.__lock if lock else nullcontext()):
            if base_path is None:
                base_path = PathUtils.get_base_path()

            env_path = os.path.join(base_path, file_name)

            returned_value = True

            if not load_dotenv(dotenv_path=env_path, override=override):
                warning_msg = f"Environment file not found. The application will rely solely on system environment variables. Please verify the .env file in {base_path}."
                logger.warning(warning_msg)
                returned_value = False
            else:
                logger.info("Env file has loaded successfully.")

            EnvManager.__env_data = os.environ
            EnvManager.__loaded = True

            return returned_value

    @staticmethod
    def get(key, default=None):
        with EnvManager.__lock:
            if (not EnvManager.__loaded):
                EnvManager.load_env(lock=False)
        return EnvManager.__env_data.get(key, default)
