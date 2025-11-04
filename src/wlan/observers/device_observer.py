import logging
from typing import Callable, List, Union

import pandas as pd

from wlan.enums import DeviceChangeEvent
from wlan.exceptions import DataParsingError
from wlan.schemas import StandardColumns as S

logger = logging.getLogger(__name__)


class DeviceChangeNotifier:
    """Monitor device changes and notify when devices connect or disconnect.

    This class tracks devices by MAC address and triggers notifications when:
    - Initial devices are discovered (event=START)
    - New devices connect (event=CONNECTED)
    - Devices disconnect (event=DISCONNECTED)
    """

    def __init__(self, notify_functions: Union[Callable, List[Callable]]):
        """Initialize the notifier with callback function(s).

        Args:
            notify_functions: Single function or list of functions to call on changes.
                            Each function should accept (df: pd.DataFrame, event: DeviceChangeEvent)

        Raises:
            ValueError: If notify_functions is empty or invalid
        """
        if isinstance(notify_functions, Callable):
            self.notify_functions = [notify_functions]
        elif isinstance(notify_functions, list):
            if not notify_functions:
                raise ValueError("notify_functions list cannot be empty")
            if not all(callable(f) for f in notify_functions):
                raise ValueError(
                    "All items in notify_functions must be callable")
            self.notify_functions = notify_functions
        else:
            raise ValueError(
                "notify_functions must be a callable or list of callables")

        self.cached_df: pd.DataFrame = None
        self.is_first_run = True
        logger.info(
            f"DeviceChangeNotifier initialized with {len(self.notify_functions)} notify function(s)")

    def _validate_dataframe(self, df: pd.DataFrame) -> None:
        """Validate that DataFrame has required MAC address column.

        Args:
            df: DataFrame to validate

        Raises:
            DataParsingError: If DataFrame is invalid or missing MAC column
        """
        if df is None:
            raise DataParsingError("DataFrame cannot be None")

        if not isinstance(df, pd.DataFrame):
            raise DataParsingError(
                f"Expected pandas DataFrame, got {type(df)}")

        if df.empty:
            logger.warning("Received empty DataFrame")
            return

        if S.MAC_ADDRESS not in df.columns:
            raise DataParsingError(
                f"DataFrame must contain '{S.MAC_ADDRESS}' column")

    def _notify(self, df: pd.DataFrame, event: DeviceChangeEvent) -> None:
        """Call all notify functions with the given data.

        Args:
            df: DataFrame to send to notify functions
            event: Event type indicating the change
        """
        if df.empty:
            logger.debug(
                f"Skipping notification for empty DataFrame with event '{event.value}'")
            return

        logger.info(
            f"Notifying {len(self.notify_functions)} function(s) with {len(df)} device(s), event='{event.value}'")

        for func in self.notify_functions:
            try:
                func(df, event)
            except Exception as e:
                logger.error(
                    f"Error in notify function {func.__name__}: {e}", exc_info=True)

    def _get_mac_set(self, df: pd.DataFrame) -> set:
        """Extract set of MAC addresses from DataFrame.

        Args:
            df: DataFrame containing MAC addresses

        Returns:
            set: Set of MAC addresses
        """
        if df.empty:
            return set()
        return set(df[S.MAC_ADDRESS].values)

    def process(self, df: pd.DataFrame) -> None:
        """Process new DataFrame and notify on changes.

        Args:
            df: New DataFrame to process

        Raises:
            DataParsingError: If DataFrame is invalid
        """
        # Validate DataFrame
        self._validate_dataframe(df)

        # Handle first run
        if self.is_first_run:
            logger.info(f"First run: caching {len(df)} device(s)")
            self.cached_df = df.copy()
            self.is_first_run = False
            self._notify(df, event=DeviceChangeEvent.START)
            return

        # Handle empty DataFrame
        if df.empty:
            if self.cached_df is not None and not self.cached_df.empty:
                logger.info(
                    f"All {len(self.cached_df)} device(s) disconnected")
                self._notify(self.cached_df,
                             event=DeviceChangeEvent.DISCONNECTED)
                self.cached_df = df.copy()
            return

        # Compare with cached data
        cached_macs = self._get_mac_set(self.cached_df)
        current_macs = self._get_mac_set(df)

        # Find new devices (connected)
        new_macs = current_macs - cached_macs
        if new_macs:
            connected_df = df[df[S.MAC_ADDRESS].isin(new_macs)]
            logger.info(f"Found {len(connected_df)} new device(s)")
            self._notify(connected_df, event=DeviceChangeEvent.CONNECTED)

        # Find removed devices (disconnected)
        removed_macs = cached_macs - current_macs
        if removed_macs:
            disconnected_df = self.cached_df[self.cached_df[S.MAC_ADDRESS].isin(
                removed_macs)]
            logger.info(f"Found {len(disconnected_df)} disconnected device(s)")
            self._notify(disconnected_df, event=DeviceChangeEvent.DISCONNECTED)

        # Update cache
        self.cached_df = df.copy()

        if not new_macs and not removed_macs:
            logger.debug("No device changes detected")

    def reset(self) -> None:
        """Reset the notifier state (clear cache and set to first run)."""
        logger.info("Resetting DeviceChangeNotifier state")
        self.cached_df = None
        self.is_first_run = True
