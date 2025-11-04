import logging

import pandas as pd
import telebot
from telebot.apihelper import ApiTelegramException

from wlan.enums import DeviceChangeEvent
from wlan.managers import ConfigManager, EnvManager
from wlan.exceptions import APIError

logger = logging.getLogger(__name__)


class TelegramNotifier:
    """Send device change notifications via Telegram.

    This class integrates with DeviceChangeNotifier to send formatted
    messages to a Telegram chat when devices connect or disconnect.
    """

    def __init__(self):
        """Initialize Telegram bot with credentials from configuration.

        Raises:
            ValueError: If bot token or chat ID is not configured
            APIError: If bot initialization fails
        """
        self.bot_token = EnvManager.get("TELEGRAM_BOT_TOKEN")
        self.chat_id = ConfigManager.get("telegram.chat_id")

        if not self.bot_token:
            raise ValueError(
                "TELEGRAM_BOT_TOKEN not found in environment variables")

        if not self.chat_id:
            raise ValueError("telegram.chat_id not found in configuration")

        try:
            self.bot = telebot.TeleBot(self.bot_token)
            logger.info("TelegramNotifier initialized successfully")
        except Exception as e:
            logger.error(f"Failed to initialize Telegram bot: {e}")
            raise APIError(f"Failed to initialize Telegram bot: {e}") from e

    def _format_device_info(self, device_row: pd.Series) -> str:
        """Format a single device's information as a string.

        Args:
            device_row: Series containing device information

        Returns:
            str: Formatted device information
        """
        lines = []
        for column, value in device_row.items():
            if pd.notna(value):  # Skip NaN values
                lines.append(f"  • {column}: {value}")
        return "\n".join(lines)

    def _format_message(self, df: pd.DataFrame, event: DeviceChangeEvent) -> str:
        """Format notification message based on event type and DataFrame.

        Args:
            df: DataFrame containing device information
            event: Type of device change event

        Returns:
            str: Formatted message ready to send
        """
        # Event emoji and title
        event_config = {
            DeviceChangeEvent.START: ("🚀", "Initial Devices Discovered"),
            DeviceChangeEvent.CONNECTED: ("✅", "New Device(s) Connected"),
            DeviceChangeEvent.DISCONNECTED: ("❌", "Device(s) Disconnected")
        }

        emoji, title = event_config.get(event, ("ℹ️", "Device Update"))

        # Build message header
        device_count = len(df)
        device_word = "device" if device_count == 1 else "devices"
        message_parts = [
            f"{emoji} <b>{title}</b>",
            f"<b>Count:</b> {device_count} {device_word}",
            ""
        ]

        # Add device details
        for idx, (_, device) in enumerate(df.iterrows(), 1):
            message_parts.append(f"<b>Device #{idx}:</b>")
            message_parts.append(self._format_device_info(device))
            message_parts.append("")  # Empty line between devices

        return "\n".join(message_parts)

    def send_notification(self, df: pd.DataFrame, event: DeviceChangeEvent) -> None:
        """Send device change notification to Telegram.

        This method is designed to be used as a callback for DeviceChangeNotifier.

        Args:
            df: DataFrame containing device information
            event: Type of device change event

        Raises:
            APIError: If message sending fails
        """
        if df.empty:
            logger.warning(
                f"Skipping Telegram notification for empty DataFrame (event: {event.value})")
            return

        try:
            message = self._format_message(df, event)

            self.bot.send_message(
                chat_id=self.chat_id,
                text=message,
                parse_mode='HTML'
            )

            logger.info(
                f"Telegram notification sent successfully: {event.value}, {len(df)} device(s)")

        except ApiTelegramException as e:
            logger.error(f"Telegram API error: {e}")
            raise APIError(f"Failed to send Telegram message: {e}") from e
        except Exception as e:
            logger.error(
                f"Unexpected error sending Telegram notification: {e}")
            raise APIError(f"Failed to send Telegram notification: {e}") from e

    def test_connection(self) -> bool:
        """Test Telegram bot connection by sending a test message.

        Returns:
            bool: True if connection is successful

        Raises:
            APIError: If connection test fails
        """
        try:
            self.bot.send_message(
                chat_id=self.chat_id,
                text="🔔 <b>Telegram Notifier Test</b>\n\nConnection successful!",
                parse_mode='HTML'
            )
            logger.info("Telegram connection test successful")
            return True
        except ApiTelegramException as e:
            logger.error(f"Telegram connection test failed: {e}")
            raise APIError(f"Telegram connection test failed: {e}") from e
