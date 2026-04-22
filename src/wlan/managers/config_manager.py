import logging
import os
from contextlib import nullcontext
from threading import RLock
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
    __file_name: str = "config.yaml"
    __base_path: str = None
    __lock = RLock()

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
                ConfigManager.__file_name = file_name
                ConfigManager.__base_path = base_path

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
    def reload_config(file_name="config.yaml", base_path: str = None) -> bool:
        """Forces reloading the config file from disk."""
        with ConfigManager.__lock:
            ConfigManager.__loaded = False
            ConfigManager.__config_data = None
        return ConfigManager.load_config(file_name=file_name, base_path=base_path, lock=True)

    @staticmethod
    def save_config(file_name: str = None, base_path: str = None) -> bool:
        """Persists current in-memory config data to disk."""
        with ConfigManager.__lock:
            if not ConfigManager.__loaded:
                ConfigManager.load_config(lock=False)

            target_file_name = file_name or ConfigManager.__file_name or "config.yaml"
            target_base_path = base_path or ConfigManager.__base_path or PathUtils.get_base_path()
            config_path = os.path.join(target_base_path, target_file_name)

            with open(config_path, "w", encoding="utf-8") as f:
                yaml.safe_dump(
                    ConfigManager.__config_data,
                    f,
                    default_flow_style=False,
                    sort_keys=False,
                    allow_unicode=False
                )
            logger.info("Config file saved successfully at %s", config_path)
            return True

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

    @staticmethod
    def upsert_cached_host(mac_address: str, updates: Dict[str, Any]) -> Dict[str, Any]:
        """Adds or updates one host inside `main.cached_hosts` and saves config."""
        if not isinstance(updates, dict):
            raise ValueError("updates must be a dict")

        normalized_mac = (mac_address or "").strip().lower()
        if not normalized_mac:
            raise ValueError("mac_address is required")

        with ConfigManager.__lock:
            config = ConfigManager.get_config()
            main = config.setdefault("main", {})
            cached_hosts = main.setdefault("cached_hosts", {})
            if not isinstance(cached_hosts, dict):
                cached_hosts = {}
                main["cached_hosts"] = cached_hosts

            host_data = cached_hosts.get(normalized_mac, {})
            if not isinstance(host_data, dict):
                host_data = {}

            for key, value in updates.items():
                if value is not None:
                    host_data[key] = value

            cached_hosts[normalized_mac] = host_data
            ConfigManager.save_config()
            return host_data

    @staticmethod
    def delete_cached_host(mac_address: str) -> bool:
        """Deletes one host from `main.cached_hosts` and saves config."""
        normalized_mac = (mac_address or "").strip().lower()
        if not normalized_mac:
            raise ValueError("mac_address is required")

        with ConfigManager.__lock:
            config = ConfigManager.get_config()
            cached_hosts = config.setdefault("main", {}).setdefault("cached_hosts", {})
            if not isinstance(cached_hosts, dict):
                return False

            if normalized_mac not in cached_hosts:
                return False

            del cached_hosts[normalized_mac]
            ConfigManager.save_config()
            return True
