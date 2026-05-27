"""Config flow to configure Uber Eats component."""
import logging
from typing import Optional
import voluptuous as vol

from homeassistant import core, exceptions
from homeassistant.config_entries import (
    CONN_CLASS_CLOUD_POLL,
    ConfigFlow,
    OptionsFlow,
    ConfigEntry
    )
from homeassistant.const import CONF_NAME
from homeassistant.core import callback
from homeassistant.helpers.typing import ConfigType
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .const import (
    DOMAIN,
    CONF_ACCOUNT,
    CONF_COOKIE,
    CONF_LOCALCODE,
    DEFAULT_LOCALCODE,
    LOCALCODES
)
from .data import UberEatsData

_LOGGER = logging.getLogger(__name__)

async def validate_input(hass: core.HomeAssistant, data):
    """Validate that the user input allows us to connect to DataPoint.

    Data has the keys from DATA_SCHEMA with values provided by the user.
    """

    account = data[CONF_ACCOUNT]
    cookie = data[CONF_COOKIE]
    localcode = data[CONF_LOCALCODE]
    session = async_get_clientsession(hass)

    uber_eats_data = UberEatsData(hass, session, account, cookie, localcode)
    uber_eats_data.ordered = True
    try:
        await uber_eats_data.async_update_data()
    except exceptions.ConfigEntryAuthFailed as err:
        # Surface auth failure as a form error rather than kicking the user out.
        _LOGGER.warning("Validation failed for %s: %s", account, err)
        raise CannotConnect() from err
    if uber_eats_data.account is None:
        raise CannotConnect()

    return {CONF_ACCOUNT: uber_eats_data.account}


async def _validate_with_errors(hass, user_input):
    """Run validate_input, returning (info_or_None, errors_dict)."""
    try:
        return await validate_input(hass, user_input), {}
    except CannotConnect:
        return None, {"base": "cannot_connect"}
    except Exception:  # pylint: disable=broad-except
        _LOGGER.exception("Unexpected exception")
        return None, {"base": "unknown"}

class UberEatsFlowHandler(ConfigFlow, domain=DOMAIN):
    """Handle a Uber Eats config flow."""

    VERSION = 1
    CONNECTION_CLASS = CONN_CLASS_CLOUD_POLL

    def __init__(self):
        """Initialize flow."""
        self._account: Optional[str] = None
        self._cookie: Optional[str] = None
        self._localcode: Optional[str] = None
        self._reauth_entry: Optional[ConfigEntry] = None

    @staticmethod
    @callback
    def async_get_options_flow(config_entry: ConfigEntry):
        """ get option flow """
        return OptionsFlowHandler()

    async def async_step_user(
        self,
        user_input: Optional[ConfigType] = None
    ):
        """Handle a flow initialized by the user."""
        errors = {}
        if user_input is not None:
            await self.async_set_unique_id(
                f"{user_input[CONF_ACCOUNT]}"
            )
            self._abort_if_unique_id_configured()

            info, errors = await _validate_with_errors(self.hass, user_input)
            if info is not None:
                user_input[CONF_NAME] = info[CONF_ACCOUNT]
                return self.async_create_entry(
                    title=user_input[CONF_NAME], data=user_input
                )

        data_schema = vol.Schema(
            {
                vol.Required(CONF_ACCOUNT): str,
                vol.Required(CONF_COOKIE): str,
                vol.Required(CONF_LOCALCODE, default=DEFAULT_LOCALCODE): vol.In(
                    list(LOCALCODES.keys())
                ),
            }
        )

        return self.async_show_form(
            step_id="user", data_schema=data_schema, errors=errors
        )

    async def async_step_reauth(self, entry_data):
        """Handle reauth triggered by ConfigEntryAuthFailed."""
        self._reauth_entry = self.hass.config_entries.async_get_entry(
            self.context["entry_id"]
        )
        return await self.async_step_reauth_confirm()

    async def async_step_reauth_confirm(self, user_input=None):
        """Ask the user to paste a fresh `sid` cookie."""
        errors = {}
        existing = {**self._reauth_entry.options}

        if user_input is not None:
            merged = {**existing, CONF_COOKIE: user_input[CONF_COOKIE]}
            info, errors = await _validate_with_errors(self.hass, merged)
            if info is not None:
                self.hass.config_entries.async_update_entry(
                    self._reauth_entry, options=merged
                )
                await self.hass.config_entries.async_reload(
                    self._reauth_entry.entry_id
                )
                return self.async_abort(reason="reauth_successful")

        return self.async_show_form(
            step_id="reauth_confirm",
            data_schema=vol.Schema({vol.Required(CONF_COOKIE): str}),
            description_placeholders={
                "account": existing.get(CONF_ACCOUNT, "")
            },
            errors=errors,
        )

    @property
    def _name(self):
        # pylint: disable=no-member
        # https://github.com/PyCQA/pylint/issues/3167
        return self.context.get(CONF_NAME)

    @_name.setter
    def _name(self, value):
        # pylint: disable=no-member
        # https://github.com/PyCQA/pylint/issues/3167
        self.context[CONF_NAME] = value
        self.context["title_placeholders"] = {"name": self._account}


class OptionsFlowHandler(OptionsFlow):
    # pylint: disable=too-few-public-methods
    """Handle options flow changes."""

    async def async_step_init(self, user_input=None):
        """Manage the options."""
        errors = {}
        account = self.config_entry.options.get(CONF_ACCOUNT, '')
        cookie = self.config_entry.options.get(CONF_COOKIE, '')
        localcode = self.config_entry.options.get(CONF_LOCALCODE, '')

        if user_input is not None:
            user_input[CONF_ACCOUNT] = account
            info, errors = await _validate_with_errors(self.hass, user_input)
            if info is not None:
                user_input[CONF_NAME] = info[CONF_ACCOUNT]
                return self.async_create_entry(
                    title=user_input[CONF_NAME], data=user_input
                )

        return self.async_show_form(
            step_id="init",
            data_schema=vol.Schema(
                {
                    vol.Required(CONF_COOKIE, default=cookie): str,
                    vol.Required(CONF_LOCALCODE, default=localcode): vol.In(
                        list(LOCALCODES.keys())
                    )
                }
            ),
            errors=errors
        )

class CannotConnect(exceptions.HomeAssistantError):
    """Error to indicate we cannot connect."""
