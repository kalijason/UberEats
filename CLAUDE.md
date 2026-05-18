# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

A Home Assistant custom integration (`uber_eats`) that polls Uber Eats' active-orders API and exposes the current order status as Home Assistant entities. Distributed via HACS — there is no Python package, no test suite, and no build step. "Running" the code means installing it into a Home Assistant instance.

Domain: `uber_eats` (constant in `custom_components/uber_eats/const.py`). Manifest declares only `requests` as a Python requirement and targets `homeassistant >= 2024.1.0` (per `hacs.json`).

## Installation / "How to run"

There are no `make`, `pytest`, `npm`, or lint commands wired up. To exercise changes:

- Copy `custom_components/uber_eats/` into the `config/custom_components/` directory of a Home Assistant instance, then restart HA.
- Or use HACS → Custom repositories → add `kalijason/UberEats` as an Integration.
- Configure via HA UI: Configuration → Integrations → Add Integration → Uber Eats. Requires the user's Uber Eats `sid` cookie (see `README.md` for the browser DevTools steps to grab it).

When bumping a release, update `version` in `custom_components/uber_eats/manifest.json`.

## Architecture

The integration follows the standard Home Assistant config-entry + DataUpdateCoordinator pattern. One coordinator per configured account fans out to five platform entities sharing one fetched payload.

**Data flow (single source of truth):**

1. `__init__.py::async_setup_entry` builds a `UberEatsData` instance and wraps it in a `DataUpdateCoordinator` polling every `DEFAULT_SCAN_INTERVAL` (1 minute). Both are stashed in `hass.data[DOMAIN][entry_id]` under keys `UBER_EATS_DATA` / `UBER_EATS_COORDINATOR`.
2. `data.py::UberEatsData.async_update_data` POSTs to `https://www.ubereats.com/api/getActiveOrdersV1` with the user's `sid` cookie and parses `data.orders` from the JSON response into `self.orders[account]["orders"]`.
3. Each platform (`sensor`, `binary_sensor`, `device_tracker`, `image`, `button`) reads from the same `UberEatsData` instance — the sensor's `async_update` re-walks the cached orders structure rather than re-fetching.

**Polling gating logic in `UberEatsData`** — non-obvious and easy to break:

- `self.ordered` and `self.expired` flags gate the actual HTTP call. The fetch only fires when `not expired and (ordered or force_update)`.
- `ordered` is flipped to `True` by `UberEatsButton.async_press` (the "Order" button) and reset to `False` when the active-orders list becomes empty. This is how the integration avoids hammering the API when the user isn't actively ordering.
- A `force_update` is triggered every 300 seconds via `_last_check`, so a fresh poll still happens periodically even without `ordered`.
- Two cookies (`cookie` and `cookie2`) are supported as a failover: on a 403/expired response, `expired` flips to `True` and the next cycle swaps `self._cookie` between `_cookie1` and `_cookie2`.

**Order payload shape** (parsed in `sensor.py::async_update`): each order has `feedCards[]` (with `type == "status"` or `"courier"`), `contacts[]` (with `type == "COURIER"`), `activeOrderOverview.title` (restaurant name), and `backgroundFeedCards[].mapEntity[]` (courier lat/long, used by `device_tracker.py`). Multiple concurrent orders are flattened by appending `_<index+1>` suffixes to attribute keys after the first.

**Platforms registered** (`const.PLATFORMS`): `binary_sensor` (new-order flag), `button` (sets `ordered=True` to force next poll), `device_tracker` (courier GPS), `image` (courier photo), `sensor` (order count + all attributes). All entities tie to the same HA device via `device_info` keyed on `(DOMAIN, account)`.

**Config flow** (`config_flow.py`): two-step pattern — initial setup collects account + both cookies + localcode; `OptionsFlowHandler` lets users refresh cookies later without re-adding the integration. `__init__.py` migrates `entry.data` → `entry.options` on first setup so options-flow edits are authoritative.

## Conventions for changes here

- Keep `PLATFORMS` and the per-platform `async_setup_entry` signatures in sync — `__init__.py` forwards setup to every name in that list via `async_forward_entry_setups`.
- New attributes exposed by the sensor must be added to `ATTR_LIST` in `const.py` (it's used to zero-initialize attrs each update cycle in `sensor.py`).
- When adding fields read from the Uber Eats JSON, guard with `.get()` / list-index checks — the upstream shape changes without notice and the existing parser swallows exceptions only at the outer `try` in `sensor.async_update`.
- `manifest.json` and `hacs.json` both pin metadata; release bumps need `manifest.json::version`.
