import logging
import os
from contextlib import nullcontext
from threading import Lock
from typing import Any, Dict

import yaml

from wlan.descriptors import static_property
from wlan.utils import PathUtils

logger = logging.getLogger(__name__)


class ConfigManager:
    """
    Manages loading and accessing the config.yaml file.
    Uses a thread-safe, lazy-loading singleton pattern.
    """
    __loaded = False
    __config_data: Dict = None
    __lock = Lock()

    @static_property
    def loaded(cls) -> bool:
        """Checks if the config file has been loaded."""
        with ConfigManager.__lock:
            return ConfigManager.__loaded

    @staticmethod
    def load_config(file_name="config.yaml", base_path: str = None, lock=False) -> bool:
        """
        Loads the config file into the class cache in a thread-safe way.
        This contains the logic you provided.
        """
        with (ConfigManager.__lock if lock else nullcontext()):
            if ConfigManager.__loaded:
                return True

            if base_path is None:
                base_path = PathUtils.get_base_path()

            config_path = os.path.join(base_path, file_name)

            try:
                with open(config_path, 'r', encoding='utf-8') as f:
                    config = yaml.safe_load(f)

                    if not isinstance(config, dict):
                        error_msg = f"CRITICAL ERROR: can't read `{config_path}` as dict."
                        logger.error(error_msg)
                        raise Exception(error_msg)
                    else:
                        logger.info("Config file has loaded successfully.")

                ConfigManager.__config_data = config
                ConfigManager.__loaded = True

                return True

            except FileNotFoundError as e:
                error_msg = f"CRITICAL ERROR: 'config.yaml' not found at {config_path}"
                logger.error(error_msg)
                raise FileNotFoundError(error_msg) from e
            except Exception as e:
                error_msg = f"Error loading 'config.yaml': {e}"
                logger.error(error_msg)
                raise Exception(error_msg) from e

    @staticmethod
    def get_config() -> Dict:
        """
        Gets the full, cached configuration dictionary.
        Triggers lazy-loading if config isn't loaded yet.
        """
        with ConfigManager.__lock:
            if (not ConfigManager.__loaded):
                ConfigManager.load_config(lock=False)

            return ConfigManager.__config_data

    @staticmethod
    def get(key: str, default: Any = None) -> Any:
        """
        Gets a specific value from the loaded config.
        Supports simple dot notation for nested keys (e.g., "main.logging_level").
        """
        config = ConfigManager.get_config()

        if config is None:
            return default

        try:
            keys = key.split('.')
            value = config
            for k in keys:
                value = value[k]
            return value
        except (KeyError, TypeError):
            return default
