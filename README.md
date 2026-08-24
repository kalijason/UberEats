# Uber Eats for Home Assistant

Track your active Uber Eats order from Home Assistant — order status, courier location,
courier photo, and the restaurant name, exposed as entities you can build automations on.

> **Use this integration at your own risk.** It talks to an undocumented Uber Eats
> endpoint using your session cookie. The upstream API changes without notice.

[繁體中文說明](README_zh-Hant.md)

## Credit

This is a derivative of [**tsunglung/UberEats**](https://github.com/tsunglung/UberEats)
by [@tsunglung](https://github.com/tsunglung), who wrote the original integration and
everything it does well. It is MIT-licensed, and that licence and copyright carry over
unchanged — see [LICENSE](LICENSE).

This repository diverged from upstream at commit `512c57f`. Every commit up to that
point is tsunglung's, with the original authorship and commit hashes intact, so you can
verify the base against upstream yourself.

It is maintained separately rather than as a GitHub fork. See
[docs/adr/0001-standalone-repo-not-fork.md](docs/adr/0001-standalone-repo-not-fork.md)
for why.

## What's different in this fork

| Change | Why it matters |
|---|---|
| **Silent session-expiry detection + reauth flow** | The Uber Eats API returns `HTTP 200` with an empty payload when the `sid` cookie expires — not a `403`. Upstream's expiry check never fires, so `binary_sensor.new_order` just stays `False` forever with no visible error. This fork inspects the response shape, raises `ConfigEntryAuthFailed`, and Home Assistant shows a re-authentication prompt where you paste a fresh cookie without removing the integration. |
| **Options flow fixed for modern Home Assistant** | Opening *Configure* raised a 500 on newer releases. |
| **No more `HTTP 400` when idle** | The courier image entity fell back to a Wikipedia placeholder URL that rejects Home Assistant's requests, logging an error on every poll with no active order. |
| **Dropped the unused `requests` dependency** | The integration is fully `aiohttp`-based; `requests` was declared but never used. |
| **Single cookie instead of two** | The second-cookie failover never worked as intended and doubled the setup burden. |

## Requirements

**Home Assistant 2024.12 or newer.** The options flow relies on the framework-provided
`OptionsFlow.config_entry` property, which does not exist before 2024.12 — on older
releases the integration installs but *Configure* raises `AttributeError`.

## Install

**Via HACS** — HACS → Integrations → ⋮ (top right) → Custom repositories →
URL `kalijason/UberEats`, Category `Integration`. Then install and restart Home Assistant.

**Manually** — copy `custom_components/uber_eats/` into the `custom_components/` folder
of your Home Assistant config directory and restart.

## Setup

### 1. Get your `sid` cookie

The integration authenticates with the session cookie from your browser. It expires
after roughly a month, and you will need to repeat this when it does.

1. Open [ubereats.com](https://www.ubereats.com/) and sign in.
2. Open developer tools — <kbd>F12</kbd>, or <kbd>Ctrl</kbd>+<kbd>Shift</kbd>+<kbd>I</kbd>
   (<kbd>⌘</kbd>+<kbd>⌥</kbd>+<kbd>I</kbd> on macOS).
3. Go to the **Application** tab → **Storage** → **Cookies** → `https://www.ubereats.com`.
4. Find the cookie named **`sid`**. If several match, take the first.
5. Copy the whole **Value** — a long string beginning `QA.` and ending `=`.

Treat that string like a password. It grants access to your Uber Eats account.

### 2. Add the integration

1. **Settings → Devices & Services → Add Integration → Uber Eats**.
   If it is not listed, refresh the page; if it is still missing, clear the browser cache.
2. Enter your account name and the `sid` cookie. All fields are required.

## When the cookie expires

You will get a **Reconfigure** prompt on the integration card — open it and paste a fresh
`sid`. Nothing needs removing or re-adding, and your entity IDs stay the same.

If you would rather do it manually: **Settings → Devices & Services → Uber Eats →
Configure**.

## Entities

| Entity | What it gives you |
|---|---|
| `sensor.uber_eats_<account>_orders` | Active order count, plus every parsed order attribute |
| `binary_sensor.uber_eats_<account>_new_order` | Whether an order is currently active |
| `device_tracker.uber_eats_<account>_courier` | The courier's live GPS position |
| `image.uber_eats_<account>_courier` | The courier's photo |
| `button.uber_eats_<account>_order` | Forces the next poll to actually hit the API |

## Licence

MIT — see [LICENSE](LICENSE). Copyright © 2021 tsunglung.
