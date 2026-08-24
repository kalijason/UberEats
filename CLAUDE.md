# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

A Home Assistant custom integration (`uber_eats`) that polls Uber Eats' active-orders API and exposes the current order status as Home Assistant entities. Distributed via HACS — there is no Python package, no test suite, and no build step. "Running" the code means installing it into a Home Assistant instance.

Domain: `uber_eats` (constant in `custom_components/uber_eats/const.py`). The manifest declares **no** Python requirements (`"requirements": []`) — the integration is entirely `aiohttp`-based. Minimum Home Assistant is **2024.12.0** (per `hacs.json`): the options flow relies on the framework-provided `OptionsFlow.config_entry` property, which does not exist before that release.

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

- `self.ordered` gates the actual HTTP call: the fetch only fires when `ordered or force_update`, and is short-circuited entirely once `self._auth_failed` is set.
- `ordered` is flipped to `True` by `UberEatsButton.async_press` (the "Order" button) and reset to `False` when the active-orders list becomes empty. This is how the integration avoids hammering the API when the user isn't actively ordering.
- A `force_update` is triggered every 300 seconds via `_last_check`, so a fresh poll still happens periodically even without `ordered`.
- **Silent session expiry is the non-obvious part.** When the `sid` cookie expires, the API answers
  `HTTP 200` with no orders payload — not a `403`. A naive status-code check therefore never fires, and
  the integration would sit there reporting success forever. `data.py` inspects the *response shape* to
  tell "no active orders" apart from "session dead", sets `self._auth_failed`, and raises
  `ConfigEntryAuthFailed` so Home Assistant surfaces a reauth prompt. `config_flow.py::async_step_reauth_confirm`
  lets the user paste a fresh `sid` in place, keeping the entry and its entity IDs.
- A single cookie is used (`CONF_COOKIE`). The old two-cookie failover and the write-only `expired` flag
  were both removed — if you see them referenced anywhere, that reference is stale.

**Order payload shape** (parsed in `sensor.py::async_update`): each order has `feedCards[]` (with `type == "status"` or `"courier"`), `contacts[]` (with `type == "COURIER"`), `activeOrderOverview.title` (restaurant name), and `backgroundFeedCards[].mapEntity[]` (courier lat/long, used by `device_tracker.py`). Multiple concurrent orders are flattened by appending `_<index+1>` suffixes to attribute keys after the first.

**Platforms registered** (`const.PLATFORMS`): `binary_sensor` (new-order flag), `button` (sets `ordered=True` to force next poll), `device_tracker` (courier GPS), `image` (courier photo), `sensor` (order count + all attributes). All entities tie to the same HA device via `device_info` keyed on `(DOMAIN, account)`.

**Config flow** (`config_flow.py`): initial setup collects account + the single `sid` cookie + localcode. `OptionsFlowHandler` lets users refresh the cookie later without re-adding the integration, and `async_step_reauth_confirm` handles the same refresh when Home Assistant triggers reauth after a silent expiry. `OptionsFlowHandler` takes no constructor arguments and reads the framework-provided `self.config_entry` — this is what pins the 2024.12 minimum. `__init__.py` migrates `entry.data` → `entry.options` on first setup so options-flow edits are authoritative.

## Conventions for changes here

- Keep `PLATFORMS` and the per-platform `async_setup_entry` signatures in sync — `__init__.py` forwards setup to every name in that list via `async_forward_entry_setups`.
- New attributes exposed by the sensor must be added to `ATTR_LIST` in `const.py` (it's used to zero-initialize attrs each update cycle in `sensor.py`).
- When adding fields read from the Uber Eats JSON, guard with `.get()` / list-index checks — the upstream shape changes without notice and the existing parser swallows exceptions only at the outer `try` in `sensor.async_update`.
- `manifest.json` and `hacs.json` both pin metadata; release bumps need `manifest.json::version`.
