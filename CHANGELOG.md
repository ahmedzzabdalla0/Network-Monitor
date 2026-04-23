# Changelog

## [1.2.1] - 2026-04-22

### Fixed

- Prevented crash when all threaded data-source results are `None` by validating DataFrames before merge.
- Improved data-source retry flow with bounded retries and safe empty fallback.
- Updated Telegram notification formatting to show `Name/Names` right after status.
- Updated `👥 Devices Now` output to include full per-device details.

## [1.2.0] - 2026-04-22

### Added

- Telegram bot menu with runtime commands:
  - show current connected devices
  - start/stop monitor loop
  - retry after crash
  - reload `config.yaml`
  - add/update/delete cached hosts in config
- Crash notification message to Telegram with retry instruction.

### Changed

- Version bumped to `1.2.0`.

### To Do

- Add configurable threshold in `ZyxelClient` to confirm disconnection using multiple failed requests
  - Introduce `disconnect_confirmations` (or similar) in the config file
  - Require N consecutive failed requests before marking a user as disconnected
  - Apply a default value if the config entry is missing
  - Add logging for each confirmation attempt (optional)
