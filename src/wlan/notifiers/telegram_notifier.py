import logging
import threading
from html import escape
from typing import Callable, Dict, Optional

import pandas as pd
import telebot
from telebot.apihelper import ApiTelegramException
from telebot import types

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
            self.menu_keyboard = self._build_menu_keyboard()
            self._polling_thread: Optional[threading.Thread] = None
            self._control_callbacks: Dict[str, Callable] = {}
            self._handlers_registered = False
            logger.info("TelegramNotifier initialized successfully")
        except Exception as e:
            logger.error(f"Failed to initialize Telegram bot: {e}")
            raise APIError(f"Failed to initialize Telegram bot: {e}") from e

    def _build_menu_keyboard(self):
        keyboard = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
        keyboard.add(
            types.KeyboardButton("👥 Devices Now"),
            types.KeyboardButton("📋 Cached Hosts"),
        )
        keyboard.add(
            types.KeyboardButton("▶️ Start"),
            types.KeyboardButton("⏸ Stop"),
        )
        keyboard.add(
            types.KeyboardButton("🔁 Retry"),
            types.KeyboardButton("🔄 Reload Config"),
        )
        keyboard.add(types.KeyboardButton("ℹ️ Status"))
        return keyboard

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
                lines.append(f"  • {escape(str(column))}: {escape(str(value))}")
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
        display_names = []
        if "Name" in df.columns:
            raw_names = [
                str(value).strip()
                for value in df["Name"].tolist()
                if pd.notna(value) and str(value).strip()
            ]
            known_names = [name for name in raw_names if name.lower() != "unknown"]
            if known_names:
                display_names = known_names
            elif raw_names:
                # Keep explicit Unknown instead of falling back to MAC.
                display_names = ["Unknown"]
        elif "MAC" in df.columns:
            display_names = [str(mac) for mac in df["MAC"].tolist() if pd.notna(mac)]

        names_label = "Name" if len(display_names) == 1 else "Names"
        names_value = ", ".join(display_names) if display_names else "Unknown"
        message_parts = [
            f"{emoji} <b>{title}</b>",
            f"<b>{names_label}:</b> {escape(names_value)}",
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

    def send_text(self, message: str) -> None:
        """Send plain HTML-formatted text message."""
        try:
            self.bot.send_message(
                chat_id=self.chat_id,
                text=message,
                parse_mode='HTML'
            )
        except Exception as e:
            logger.error("Failed to send Telegram text message: %s", e)

    def send_runtime_error(self, error: Exception) -> None:
        """Send a human-friendly crash message with retry instruction."""
        error_name = type(error).__name__
        error_details = escape(str(error))
        message = (
            "🚨 <b>WLAN Monitor Crash Detected</b>\n"
            f"<b>Type:</b> <code>{error_name}</code>\n"
            f"<b>Details:</b> <code>{error_details}</code>\n\n"
            "Bot switched to safe stop mode.\n"
            "Use <code>/retry</code> or press <b>🔁 Retry</b> to try again."
        )
        self.send_text(message)

    def _format_devices_snapshot(self, df: pd.DataFrame) -> str:
        if df is None or df.empty:
            return "👥 <b>Devices Now</b>\nNo connected devices found."

        max_devices = 20
        rows = []
        for index, (_, row) in enumerate(df.head(max_devices).iterrows(), 1):
            name = escape(str(row.get("Name", "Unknown")))
            rows.append(
                f"<b>Device #{index}: {name}</b>\n"
                f"{self._format_device_info(row)}"
            )

        extra = ""
        if len(df) > max_devices:
            extra = f"\n... and {len(df) - max_devices} more device(s)"

        return (
            f"👥 <b>Devices Now</b>\n"
            f"<b>Count:</b> {len(df)}\n\n" +
            "\n\n".join(rows) +
            extra
        )

    def _format_cached_hosts(self) -> str:
        cached_hosts = ConfigManager.get("main.cached_hosts", {})
        if not isinstance(cached_hosts, dict) or not cached_hosts:
            return "📋 <b>Cached Hosts</b>\nNo cached hosts in config."

        lines = ["📋 <b>Cached Hosts</b>"]
        for mac, host_data in cached_hosts.items():
            name = host_data.get("Name", "Unknown")
            device_type = host_data.get("Device Type", "Unknown")
            lines.append(
                f"- <code>{escape(str(mac))}</code> → "
                f"{escape(str(name))} ({escape(str(device_type))})"
            )
        return "\n".join(lines)

    def _build_menu_text(self) -> str:
        return (
            "🤖 <b>WLAN Monitor Commands</b>\n\n"
            "<b>Quick actions:</b>\n"
            "- /devices → List currently connected devices\n"
            "- /start_monitor → Resume monitoring loop\n"
            "- /stop_monitor → Pause monitoring loop\n"
            "- /retry → Retry login and resume after crash\n"
            "- /reload_config → Reload config.yaml\n\n"
            "<b>Manage cached hosts:</b>\n"
            "- /host_set &lt;mac&gt; &lt;name&gt;|&lt;device_type&gt;\n"
            "  Example: <code>/host_set aa:bb:cc:dd:ee:ff Ahmed|PHONE</code>\n"
            "- /host_del &lt;mac&gt;\n"
            "  Example: <code>/host_del aa:bb:cc:dd:ee:ff</code>\n"
            "- /hosts → Show cached hosts\n"
        )

    def register_control_handlers(
        self,
        *,
        get_devices: Callable[[], pd.DataFrame],
        start_monitor: Callable[[], str],
        stop_monitor: Callable[[], str],
        retry_monitor: Callable[[], str],
        reload_config: Callable[[], str],
        upsert_host: Callable[[str, str, str], str],
        delete_host: Callable[[str], str],
        get_status: Callable[[], str],
    ) -> None:
        """Register Telegram command handlers for runtime controls."""
        self._control_callbacks = {
            "get_devices": get_devices,
            "start_monitor": start_monitor,
            "stop_monitor": stop_monitor,
            "retry_monitor": retry_monitor,
            "reload_config": reload_config,
            "upsert_host": upsert_host,
            "delete_host": delete_host,
            "get_status": get_status,
        }

        if self._handlers_registered:
            return

        @self.bot.message_handler(commands=['start', 'menu', 'help'])
        def _menu(message):
            self.bot.send_message(
                message.chat.id,
                self._build_menu_text(),
                parse_mode='HTML',
                reply_markup=self.menu_keyboard
            )

        @self.bot.message_handler(commands=['devices'])
        def _devices(_message):
            df = self._control_callbacks["get_devices"]()
            self.send_text(self._format_devices_snapshot(df))

        @self.bot.message_handler(commands=['hosts'])
        def _hosts(_message):
            self.send_text(self._format_cached_hosts())

        @self.bot.message_handler(commands=['start_monitor'])
        def _start(_message):
            self.send_text(self._control_callbacks["start_monitor"]())

        @self.bot.message_handler(commands=['stop_monitor'])
        def _stop(_message):
            self.send_text(self._control_callbacks["stop_monitor"]())

        @self.bot.message_handler(commands=['retry'])
        def _retry(_message):
            self.send_text(self._control_callbacks["retry_monitor"]())

        @self.bot.message_handler(commands=['reload_config'])
        def _reload(_message):
            self.send_text(self._control_callbacks["reload_config"]())

        @self.bot.message_handler(commands=['status'])
        def _status(_message):
            self.send_text(self._control_callbacks["get_status"]())

        @self.bot.message_handler(commands=['host_set'])
        def _host_set(message):
            payload = message.text.partition(" ")[2].strip()
            if not payload:
                self.send_text(
                    "Usage:\n<code>/host_set &lt;mac&gt; &lt;name&gt;|&lt;device_type&gt;</code>"
                )
                return

            parts = payload.split(" ", 1)
            if len(parts) != 2:
                self.send_text(
                    "Invalid format.\n"
                    "Example: <code>/host_set aa:bb:cc:dd:ee:ff Ahmed|PHONE</code>"
                )
                return

            mac, value_part = parts[0], parts[1]
            name_part, sep, type_part = value_part.partition("|")
            if not sep:
                self.send_text(
                    "Missing separator '|'.\n"
                    "Example: <code>/host_set aa:bb:cc:dd:ee:ff Ahmed|PHONE</code>"
                )
                return

            name = name_part.strip()
            device_type = type_part.strip().upper()
            self.send_text(self._control_callbacks["upsert_host"](mac, name, device_type))

        @self.bot.message_handler(commands=['host_del'])
        def _host_delete(message):
            mac = message.text.partition(" ")[2].strip()
            if not mac:
                self.send_text("Usage: <code>/host_del &lt;mac&gt;</code>")
                return
            self.send_text(self._control_callbacks["delete_host"](mac))

        @self.bot.message_handler(func=lambda m: m.text == "👥 Devices Now")
        def _devices_button(message):
            _devices(message)

        @self.bot.message_handler(func=lambda m: m.text == "📋 Cached Hosts")
        def _hosts_button(message):
            _hosts(message)

        @self.bot.message_handler(func=lambda m: m.text == "▶️ Start")
        def _start_button(message):
            _start(message)

        @self.bot.message_handler(func=lambda m: m.text == "⏸ Stop")
        def _stop_button(message):
            _stop(message)

        @self.bot.message_handler(func=lambda m: m.text == "🔁 Retry")
        def _retry_button(message):
            _retry(message)

        @self.bot.message_handler(func=lambda m: m.text == "🔄 Reload Config")
        def _reload_button(message):
            _reload(message)

        @self.bot.message_handler(func=lambda m: m.text == "ℹ️ Status")
        def _status_button(message):
            _status(message)

        self._handlers_registered = True

    def start_control_bot(self) -> None:
        """Start Telegram long polling for menu/commands in background."""
        if self._polling_thread and self._polling_thread.is_alive():
            return

        def _poll():
            try:
                self.bot.infinity_polling(skip_pending=True, timeout=30, long_polling_timeout=30)
            except Exception as e:
                logger.error("Telegram polling loop stopped unexpectedly: %s", e, exc_info=True)

        self._polling_thread = threading.Thread(
            target=_poll,
            name="telegram-control-bot",
            daemon=True
        )
        self._polling_thread.start()
        logger.info("Telegram control bot polling started")

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
