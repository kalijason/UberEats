"""Common Uber Eats Data class used by both sensor and entity."""

import asyncio
import logging
from datetime import datetime
import json
from http import HTTPStatus

import aiohttp
from aiohttp.hdrs import USER_AGENT

from homeassistant.exceptions import ConfigEntryAuthFailed

from .const import (
    ATTR_HTTPS_RESULT,
    BASE_URL,
    HA_USER_AGENT,
    REQUEST_TIMEOUT,
    UBER_EATS_ORDERS
)

_LOGGER = logging.getLogger(__name__)


def _response_indicates_auth_loss(res: dict) -> bool:
    """Decide if a HTTP-200 body actually means the session is dead.

    Uber Eats returns HTTP 200 with an empty payload for an invalid `sid`
    instead of 403, so we need a content check. An explicit `status: success`
    is trusted even if the inner shape changes (defensive against schema
    drift); otherwise the rule is "no `orders` key in `data` == dead".
    """
    if not isinstance(res, dict):
        return True
    if res.get("status") == "failure":
        return True
    if res.get("status") == "success":
        return False
    data = res.get("data")
    if not isinstance(data, dict):
        return True
    return "orders" not in data


class UberEatsData():
    """Class for handling the data retrieval."""

    def __init__(self, hass, session, account, cookie, localcode):
        """Initialize the data object."""
        self._hass = hass
        self._session = session
        self._account = account
        self._cookie = cookie
        self._localcode = localcode
        self.orders = {}
        self.account = None
        self.ordered = False
        self.new_order = False
        self.uri = BASE_URL
        self.orders[account] = {}
        self._last_check = datetime.now()
        self._auth_failed = False

    def _parser_data(self, orders):
        """ parser data """
        data = []
        if isinstance(orders, dict):
            data = orders.get('orders', [])

        return data

    async def async_update_data(self):
        """Get the latest data for Uber Eats from REST service."""
        headers = {
            USER_AGENT: HA_USER_AGENT,
            "content-type": "application/json",
            "cookie": f"sid={self._cookie}",
            "x-csrf-Token": "x"
        }
        payload = {
            "orderUdid": "null",
            "timezone": "Asis/Taipei"
        }
        params = {
           "localCode": self._localcode
        }
        cookies = {
            "sid": f"{self._cookie}",
            "marketing_vistor_id": "8a8a7080-2a23-4ca3-8fd4-bba1a19bd035"
        }
        force_update = False
        now = datetime.now()

        if (int(now.timestamp() - self._last_check.timestamp()) > 300):
            force_update = True
            self._last_check = now

        if not (self.ordered or force_update):
            return self

        if self._auth_failed:
            raise ConfigEntryAuthFailed(
                f"Uber Eats session for {self._account} is awaiting reauth."
            )

        try:
            response = await self._session.request(
                "POST",
                url=self.uri,
                data=json.dumps(payload),
                params=params,
                headers=headers,
                cookies=cookies,
                timeout=REQUEST_TIMEOUT
            )
        except (aiohttp.ClientError, asyncio.TimeoutError) as err:
            _LOGGER.error("Failed fetching data for %s: %s", self._account, err)
            return self

        if response.status == HTTPStatus.FORBIDDEN:
            self.orders[self._account][ATTR_HTTPS_RESULT] = response.status
            self._auth_failed = True
            raise ConfigEntryAuthFailed(
                f"Uber Eats session for {self._account} is no longer valid "
                "(HTTP 403). Re-authenticate via the integration."
            )

        if response.status != HTTPStatus.OK:
            self.orders[self._account][ATTR_HTTPS_RESULT] = response.status
            _LOGGER.error(
                "Failed fetching data for %s (HTTP Status Code = %d)",
                self._account,
                response.status,
            )
            return self

        try:
            res = await response.json()
        except (aiohttp.ContentTypeError, json.JSONDecodeError, ValueError):
            res = {"data": None}

        if _response_indicates_auth_loss(res):
            self.orders[self._account][ATTR_HTTPS_RESULT] = HTTPStatus.UNAUTHORIZED
            self._auth_failed = True
            raise ConfigEntryAuthFailed(
                f"Uber Eats session for {self._account} returned an "
                "unauthenticated response (HTTP 200 with no orders payload). "
                "The `sid` cookie has likely expired silently."
            )

        self.orders[self._account][UBER_EATS_ORDERS] = self._parser_data(
            res.get('data', {})
        )
        if len(self.orders[self._account]) >= 1:
            self.orders[self._account][ATTR_HTTPS_RESULT] = HTTPStatus.OK
        else:
            self.orders[self._account][ATTR_HTTPS_RESULT] = HTTPStatus.NOT_FOUND
        if len(self.orders[self._account][UBER_EATS_ORDERS]) >= 1:
            self.new_order = True
        else:
            self.new_order = False
            self.ordered = False
        self.account = self._account

        return self
