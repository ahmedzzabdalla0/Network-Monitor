# WLAN Monitor

<p align="center">
  <b>Real-time home network monitoring for Zyxel Router + TP-Link Extender</b><br>
  Get instant connect/disconnect alerts in Telegram and Windows notifications.
</p>

<p align="center">
  <img alt="Python" src="https://img.shields.io/badge/Python-3.8%2B-3776AB?logo=python&logoColor=white">
  <img alt="Version" src="https://img.shields.io/badge/version-1.2.3-2ea44f">
  <img alt="Platform" src="https://img.shields.io/badge/platform-Windows-0078D6?logo=windows&logoColor=white">
  <img alt="License" src="https://img.shields.io/badge/license-MIT-blue">
</p>

---

## Why This Project?

`WLAN Monitor` continuously tracks devices on your local network, merges data from:
- **Zyxel router**
- **TP-Link extender**

Then it detects who connected/disconnected and notifies you in real time.

It is especially useful for:
- Smart-home monitoring
- Unauthorized device detection
- Family device presence tracking
- Quick network visibility from Telegram

---

## Features

- Real-time connect/disconnect detection
- Merged device view (router + extender)
- Telegram notifications with friendly formatting
- Telegram control menu with runtime commands
- Windows toast notifications
- Crash-safe mode:
  - app does **not** exit on runtime/startup failures
  - sends error details to Telegram
  - waits for `/retry`
- Editable host aliases and device types in `config.yaml`
- Reload config without restarting (`/reload_config`)

---

## Telegram Bot Controls

After startup, use `/menu` in Telegram.

### Commands

- `/devices` - show currently connected devices
- `/hosts` - show cached hosts
- `/status` - show monitor status
- `/start_monitor` - resume monitoring
- `/stop_monitor` - pause monitoring
- `/retry` - retry initialization/session after crash
- `/reload_config` - reload `config.yaml`
- `/host_set <mac> <name>|<device_type>` - add/update cached host
- `/host_del <mac>` - delete cached host

### Examples

```bash
/host_set aa:bb:cc:dd:ee:ff Ahmed|PHONE
/host_del aa:bb:cc:dd:ee:ff
```

---

## Project Structure

```text
Network Monitor/
├─ config.yaml
├─ pyproject.toml
├─ Makefile
├─ CHANGELOG.md
├─ out/                     # build/runtime artifacts
└─ src/
   └─ wlan/
      ├─ main.py            # app entrypoint + monitor loop
      ├─ router/            # Zyxel router client + encryption/decryption
      ├─ extender/          # TP-Link extender session + parsing
      ├─ observers/         # connect/disconnect change detection
      ├─ notifiers/         # Telegram + Windows notifications
      ├─ managers/          # config/env/timer managers
      ├─ schemas/           # standard column schema
      └─ mappers/           # source->standard field mapping
```

---

## Requirements

- Python `>= 3.8`
- Windows (for `winotify` desktop notifications)
- Access to:
  - Zyxel router web API
  - TP-Link extender interface
  - Telegram Bot token + chat id

---

## Installation

From project root:

```bash
pip install -e .
```

Optional dev tools:

```bash
pip install -e .[dev]
```

---

## Configuration

### 1) `config.yaml`

This file controls runtime behavior:
- polling interval (`main.wait_time`)
- output columns (`main.columns`)
- host aliases (`main.cached_hosts`)
- router/extender IP and protocol
- excluded MAC/IP lists
- Telegram chat id
- Windows notification columns

> Keep your own values in `config.yaml` and avoid sharing private network data publicly.

### 2) `.env`

Create a `.env` file in the runtime base path with required secrets:

```env
TELEGRAM_BOT_TOKEN=
EXTENDER_PASSWORD=
EXTENDER_R_SU_ENCRYPT=
EXTENDER_T_SU_ENCRYPT=

ROUTER_USERNAME=
ROUTER_PASSWORD=
ROUTER_ENCRYPTION_KEY=
ROUTER_IV=
ROUTER_ENCRYPTED_CONTENT=
ROUTER_ENCRYPTED_KEY=
ROUTER_RSA_PUBLIC_KEY=
```

---

## Run

### Main monitor (recommended)

```bash
python -m wlan.main
```

### Router-only CLI (debug/inspection)

```bash
python -m wlan.router.client
```

### Makefile shortcuts

```bash
make main
make start
make exe
```

---

## Build EXE (Windows)

```bash
make exe
```

This generates a standalone executable in `out/`.

---

## How It Works

1. Load env + config
2. Start Telegram control bot
3. Initialize router/extender sessions
4. Poll connected devices from both sources
5. Normalize and merge results
6. Apply cached host aliases
7. Detect connect/disconnect events
8. Send Telegram + Windows notifications

If an error happens:
- app enters safe stop mode
- sends crash details to Telegram
- waits for `/retry`

---

## Troubleshooting

### `Duplicated login` from router

This means the router rejected login due to an existing session.
The monitor will stay alive in safe stop mode; use `/retry` to reinitialize.

### No Telegram messages

- Check `TELEGRAM_BOT_TOKEN` in `.env`
- Check `telegram.chat_id` in `config.yaml`
- Send `/menu` to verify bot command handlers are active

### Empty device results

- Verify router/extender IPs in `config.yaml`
- Ensure credentials and encryption values are correct
- Check logs in `running.log`

---

## Versioning

- Current version: `1.2.3`
- See full history in `CHANGELOG.md`

---

## Contributing

PRs and ideas are welcome.

If you open an issue, include:
- your version
- relevant log lines
- whether issue is router, extender, or Telegram related

