"""The Uber Eats integration."""
import asyncio
import logging

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryNotReady
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .const import (
    CONF_ACCOUNT,
    CONF_COOKIE,
    CONF_LOCALCODE,
    DEFAULT_SCAN_INTERVAL,
    DEFAULT_LOCALCODE,
    DOMAIN,
    UBER_EATS_COORDINATOR,
    UBER_EATS_DATA,
    UBER_EATS_NAME,
    PLATFORMS,
    UPDATE_LISTENER
)
from .data import UberEatsData

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(hass: HomeAssistant, config_entry: ConfigEntry):
    """Set up a Uber Eats entry."""

    account = _get_config_value(config_entry, CONF_ACCOUNT, "")
    cookie1 = _get_config_value(config_entry, CONF_COOKIE, "")
    cookie2 = _get_config_value(config_entry, f"{CONF_COOKIE}2", "")
    localcode = _get_config_value(config_entry, CONF_LOCALCODE, DEFAULT_LOCALCODE)

    # migrate data (also after first setup) to options
    if config_entry.data:
        hass.config_entries.async_update_entry(config_entry, data={},
                                               options=config_entry.data)

    session = async_get_clientsession(hass)
    cookies = [cookie1, cookie2]

    uber_eats_data = UberEatsData(hass, session, account, cookies, localcode)

    uber_eats_coordinator = DataUpdateCoordinator(
        hass,
        _LOGGER,
        name=f"Uber Eats for {account}",
        update_method=uber_eats_data.async_update_data,
        update_interval=DEFAULT_SCAN_INTERVAL,
    )

    uber_eats_hass_data = hass.data.setdefault(DOMAIN, {})
    uber_eats_hass_data[config_entry.entry_id] = {
        UBER_EATS_DATA: uber_eats_data,
        UBER_EATS_COORDINATOR: uber_eats_coordinator,
        UBER_EATS_NAME: account,
    }
    uber_eats_data.expired = False
    uber_eats_data.ordered = True

    # Fetch initial data so we have data when entities subscribe
    await uber_eats_coordinator.async_refresh()
    if uber_eats_data.account is None:
        raise ConfigEntryNotReady()

    await hass.config_entries.async_forward_entry_setups(config_entry, PLATFORMS)

    update_listener = config_entry.add_update_listener(async_update_options)
    hass.data[DOMAIN][config_entry.entry_id][UPDATE_LISTENER] = update_listener

    return True


async def async_update_options(hass: HomeAssistant, config_entry: ConfigEntry):
    """Update options."""
    await hass.config_entries.async_reload(config_entry.entry_id)


async def async_unload_entry(hass: HomeAssistant, config_entry: ConfigEntry):
    """Unload a config entry."""
    unload_ok = all(
        await asyncio.gather(
            *[
                hass.config_entries.async_forward_entry_unload(config_entry, platform)
                for platform in PLATFORMS
            ]
        )
    )
    if unload_ok:
        update_listener = hass.data[DOMAIN][config_entry.entry_id][UPDATE_LISTENER]
        update_listener()
        hass.data[DOMAIN].pop(config_entry.entry_id)
        if not hass.data[DOMAIN]:
            hass.data.pop(DOMAIN)
    return unload_ok


def _get_config_value(config_entry, key, default):
    if config_entry.options:
        return config_entry.options.get(key, default)
    return config_entry.data.get(key, default)
