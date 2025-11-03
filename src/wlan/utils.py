import collections
import logging
import os
import sys
from typing import Dict, Iterable
import pandas as pd
import yaml

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
