# Changelog

## [1.2.0] - Upcoming

### To Do

- Add configurable threshold in `ZyxelClient` to confirm disconnection using multiple failed requests
  - Introduce `disconnect_confirmations` (or similar) in the config file
  - Require N consecutive failed requests before marking a user as disconnected
  - Apply a default value if the config entry is missing
  - Add logging for each confirmation attempt (optional)
