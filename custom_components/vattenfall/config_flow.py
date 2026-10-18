"""Config flow for Vattenfall Dynamic Tariffs integration."""
from __future__ import annotations

import logging
from typing import Any

import aiohttp
import async_timeout
import voluptuous as vol

from homeassistant import config_entries
from homeassistant.data_entry_flow import FlowResult
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .const import API_ENDPOINT, CONF_API_KEY, DOMAIN

_LOGGER = logging.getLogger(__name__)

STEP_USER_DATA_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_API_KEY): str,
    }
)


class ConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for Vattenfall Dynamic Tariffs."""

    VERSION = 1

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Handle the initial step."""
        errors: dict[str, str] = {}

        if user_input is not None:
            api_key = user_input[CONF_API_KEY].strip()

            await self.async_set_unique_id(DOMAIN)
            self._abort_if_unique_id_configured()

            # Validate the API key against Vattenfall
            session = async_get_clientsession(self.hass)
            try:
                async with async_timeout.timeout(15):
                    response = await session.get(
                        API_ENDPOINT, headers={"ocp-apim-subscription-key": api_key}
                    )
                    if response.status in (401, 403):
                        errors["base"] = "invalid_auth"
                    elif response.status != 200:
                        errors["base"] = "cannot_connect"
                    else:
                        data = await response.json()
                        if not isinstance(data, list) or len(data) == 0:
                            errors["base"] = "invalid_response"
                        else:
                            return self.async_create_entry(
                                title="Vattenfall Dynamic Tariffs",
                                data={CONF_API_KEY: api_key},
                            )
            except (aiohttp.ClientError, TimeoutError):
                errors["base"] = "cannot_connect"
            except Exception:
                _LOGGER.exception("Unexpected exception during Vattenfall config flow")
                errors["base"] = "unknown"

        return self.async_show_form(
            step_id="user",
            data_schema=STEP_USER_DATA_SCHEMA,
            errors=errors,
        )
