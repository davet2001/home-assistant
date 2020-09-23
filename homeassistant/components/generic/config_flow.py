"""Config flow for generic2_ipcam."""
# import my_pypi_dependency

import voluptuous as vol

from homeassistant import config_entries
from homeassistant.const import (
    CONF_AUTHENTICATION,
    CONF_NAME,
    CONF_PASSWORD,
    CONF_USERNAME,
    CONF_VERIFY_SSL,
    HTTP_BASIC_AUTHENTICATION,
    HTTP_DIGEST_AUTHENTICATION,
)
from homeassistant.components.camera import (
    PLATFORM_SCHEMA,
    DEFAULT_CONTENT_TYPE,
)

from .const import (
    DOMAIN,
    CONF_STILL_IMAGE_URL,
    CONF_STREAM_SOURCE,
    DEFAULT_NAME,
    CONF_CONTENT_TYPE,
    CONF_LIMIT_REFETCH_TO_URL_CHANGE,
    CONF_FRAMERATE,
)

PLATFORM_SCHEMA = vol.Schema(
    {
        vol.Optional(CONF_NAME, default=DEFAULT_NAME): str,
        vol.Required(
            CONF_STILL_IMAGE_URL,
            default="http://",
        ): str,
        vol.Optional(
            CONF_STREAM_SOURCE,
        ): str,
        vol.Optional(CONF_AUTHENTICATION, default=HTTP_BASIC_AUTHENTICATION): vol.In(
            [HTTP_BASIC_AUTHENTICATION, HTTP_DIGEST_AUTHENTICATION]
        ),
        vol.Optional(CONF_LIMIT_REFETCH_TO_URL_CHANGE, default=False): bool,
        vol.Optional(CONF_USERNAME): str,
        vol.Optional(CONF_PASSWORD): str,
        vol.Optional(CONF_CONTENT_TYPE, default=DEFAULT_CONTENT_TYPE): str,
        vol.Optional(CONF_FRAMERATE, default=2): int,
        vol.Optional(CONF_VERIFY_SSL, default=True): bool,
    }
)

# async def _async_has_devices(hass) -> bool:
#    """Return if there are devices that can be discovered."""
#    # TODO Check if there are any devices that can be discovered in the network.
#    devices = await hass.async_add_executor_job(my_pypi_dependency.discover)
#    return len(devices) > 0


# config_entry_flow.register_discovery_flow(
#    #   DOMAIN, "generic", _async_has_devices, config_entries.CONN_CLASS_UNKNOWN
# )


class GenericIPCamConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Example config flow."""

    async def async_step_user(self, info):
        errors = {}

        if info is not None:
            await self.async_set_unique_id(info[CONF_STILL_IMAGE_URL])
            self._abort_if_unique_id_configured()
            return self.async_create_entry(title=info[CONF_NAME], data=info)

        return self.async_show_form(
            step_id="user", data_schema=PLATFORM_SCHEMA, errors=errors
        )
