import collections
import logging
import os
import sys
from threading import Thread
from typing import Callable, Dict, Iterable, List, Tuple
import pandas as pd
import yaml
from wlan.schemas import StandardColumns as S


logger = logging.getLogger(__name__)


class DataframeUtils:
    @staticmethod
    def merge_only_on_left(left: pd.DataFrame, right: pd.DataFrame, on: str) -> pd.DataFrame:
        right_unique = right.drop(columns=[
                                  col for col in right.columns if col in left.columns and col != on])

        return pd.merge(left, right_unique, "left", on=on)

    @staticmethod
    def exclude_rows(df: pd.DataFrame, column: str, excluded_vals: Iterable) -> pd.DataFrame:
        return df[~df[column].isin(excluded_vals)]

    @staticmethod
    def finalize_dfs(*dfs: Tuple[pd.DataFrame]) -> pd.DataFrame:
        from wlan.managers import ConfigManager
        merged: pd.DataFrame = pd.concat(dfs).fillna("Unknown")
        cached_hosts = ConfigManager.get("main.cached_hosts", {})
        if not isinstance(cached_hosts, dict):
            warning_msg = "Parsing Warring: `cached_hosts` can not be parsed as `dict`."
            logger.warning(warning_msg)
            return merged

        if not S.MAC_ADDRESS in merged.columns:
            warning_msg = "NotFound Warring: `mac` not found so we can't filtered cached hosts."
            logger.warning(warning_msg)
            return merged

        for mac, cols in cached_hosts.items():
            target = merged[S.MAC_ADDRESS] == mac
            if isinstance(cols, Dict):
                for col, val in cols.items():
                    merged.loc[target, col] = val

        if S.DEVICE_TYPE in merged.columns:
            merged[S.DEVICE_TYPE] = merged[S.DEVICE_TYPE].str.upper()

        if S.MAC_ADDRESS in merged.columns:
            merged.drop_duplicates(subset=[S.MAC_ADDRESS], inplace=True)

        return merged


class PathUtils:
    @staticmethod
    def get_base_path() -> str:
        """
        Gets the base path for loading external files (like .env or config.yaml).
        Handles both frozen (.exe) and script modes.
        """
        if getattr(sys, 'frozen', False):
            # We are running in a bundled .exe
            return os.path.dirname(sys.executable)
        else:
            # We are running in a normal Python script
            return os.path.abspath(".")

    @staticmethod
    def get_bundled_path() -> str:
        if hasattr(sys, '_MEIPASS'):
            # We are running in a bundled .exe
            return sys._MEIPASS
        else:
            # We are running in a normal Python script
            return os.path.abspath(".")

    @staticmethod
    def load_config(file_name="config.yaml", base_path: str = None) -> Dict:
        if base_path is None:
            base_path = PathUtils.get_base_path()

        config_path = os.path.join(base_path, file_name)

        try:
            with open(config_path, 'r', encoding='utf-8') as f:
                config = yaml.safe_load(f)
                if not isinstance(config, dict):
                    error_msg = f"CRITICAL ERROR: can't read `{config_path}` as dict."
                    logger.error(error_msg)
                    raise Exception(error_msg) from e
                return DictWrapper(config)

        except FileNotFoundError as e:
            error_msg = f"CRITICAL ERROR: 'config.yaml' not found at {config_path}"
            logger.error(error_msg)
            raise FileNotFoundError(error_msg) from e
        except Exception as e:
            error_msg = f"Error loading 'config.yaml': {e}"
            logger.error(error_msg)
            raise Exception(error_msg) from e


class ThreadUtils:
    @staticmethod
    def fire_and_wait(*callables: Tuple[Callable]) -> Tuple:
        """Execute multiple callables concurrently and wait for all to complete.

        This method runs multiple functions in parallel using threads and waits
        for all of them to finish before returning their results in order.

        Args:
            *callables: Variable number of callable functions to execute concurrently.
                       Each callable should be a function that takes no arguments.

        Returns:
            Tuple: Results from all callables in the same order they were provided.
                  If a callable returns None, None will be in that position.

        Example:
            >>> def get_router_data():
            ...     return {"devices": 5}
            >>> def get_extender_data():
            ...     return {"devices": 3}
            >>> router_data, extender_data = fire_and_wait(get_router_data, get_extender_data)

        Note:
            - All callables are executed simultaneously in separate threads
            - The method blocks until all threads complete
            - Results maintain the original order regardless of completion time
            - No exception handling is provided - exceptions in threads will be lost
        """
        results = [None] * len(callables)
        threads: List[Thread] = []

        for i, cal in enumerate(callables):
            def wrapper(index=i, func=cal):
                results[index] = func()
            threads.append(Thread(target=wrapper))

        for thread in threads:
            thread.start()

        for thread in threads:
            thread.join()

        return tuple(results)


class DictWrapper(collections.abc.Mapping):

    def __init__(self, data):
        self._data = data

    def __getitem__(self, key):
        return self._data[key]

    def __len__(self):
        return len(self._data)

    def __iter__(self):
        return iter(self._data)

    def get(self, key, defaulf_value):
        return self._data[key] if key in self._data else defaulf_value
