"""Config flow for generic (IP Camera)."""

import imghdr
import logging

import av
import voluptuous as vol

from homeassistant import config_entries, data_entry_flow
from homeassistant.components.camera import DEFAULT_CONTENT_TYPE
from homeassistant.const import (
    CONF_AUTHENTICATION,
    CONF_NAME,
    CONF_PASSWORD,
    CONF_USERNAME,
    CONF_VERIFY_SSL,
    HTTP_BASIC_AUTHENTICATION,
    HTTP_DIGEST_AUTHENTICATION,
)

from .camera import GenericCamera
from .const import (
    CONF_CONTENT_TYPE,
    CONF_FRAMERATE,
    CONF_LIMIT_REFETCH_TO_URL_CHANGE,
    CONF_STILL_IMAGE_URL,
    CONF_STREAM_SOURCE,
    DEFAULT_IMAGE_URL,
    DEFAULT_NAME,
    DEFAULT_PASSWORD,
    DEFAULT_STREAM_SOURCE,
    DEFAULT_USERNAME,
    DOMAIN,
)

_LOGGER = logging.getLogger(__name__)

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

    async def _test_connection(self, info):
        """Verify that the camera data is valid before we add it."""
        await self.async_set_unique_id(info[CONF_STILL_IMAGE_URL])
        try:
            self._abort_if_unique_id_configured()
        except data_entry_flow.AbortFlow as e:
            if "already_configured" in str(e):
                self._errors["base"] = "still_image_already_configured"
                return False
        cam = GenericCamera(self.hass, info)
        # Minimum functionality is getting a still image
        image = await cam.async_camera_image()
        if image is None:
            self._errors["base"] = "unable_still_load"
            return False
        fmt = imghdr.what(None, h=image)
        _LOGGER.info(
            "Still image at '%s' detected format: %s", cam._still_image_url, fmt
        )
        if fmt is None:
            self._errors["base"] = "invalid_still_image"
            return False

        # Second level functionality is to get a stream.
        if info.get(CONF_STREAM_SOURCE) is not None:
            try:
                container = av.open(info.get(CONF_STREAM_SOURCE), options=None)
                video_stream = container.streams.video[0]
                if video_stream is not None:
                    return True
            except av.error.HTTPUnauthorizedError:
                self._errors["base"] = "stream_unauthorised"
            except (KeyError, IndexError):
                self._errors["base"] = "stream_novideo"
            except av.error.OSError as e:
                if "No route to host" in str(e):
                    self._errors["base"] = "stream_no_route_to_host"
            return False
        else:
            return True

    async def async_step_user(self, info):
        """Handle the start of the config flow."""

        self._errors = {}

        if info is not None:
            if await self._test_connection(info):
                return self.async_create_entry(title=info[CONF_NAME], data=info)
        else:
            info = {}
            info[CONF_NAME] = DEFAULT_NAME
            info[CONF_STILL_IMAGE_URL] = DEFAULT_IMAGE_URL
            info[CONF_STREAM_SOURCE] = DEFAULT_STREAM_SOURCE
            info[CONF_USERNAME] = DEFAULT_USERNAME
            info[CONF_PASSWORD] = DEFAULT_PASSWORD
            info[CONF_AUTHENTICATION] = HTTP_BASIC_AUTHENTICATION
            info[CONF_LIMIT_REFETCH_TO_URL_CHANGE] = False
            info[CONF_CONTENT_TYPE] = DEFAULT_CONTENT_TYPE
            info[CONF_FRAMERATE] = 2
            info[CONF_VERIFY_SSL] = True

        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema(
                {
                    vol.Optional(CONF_NAME, default=info[CONF_NAME]): str,
                    vol.Required(
                        CONF_STILL_IMAGE_URL,
                        default=info[CONF_STILL_IMAGE_URL],
                    ): str,
                    vol.Optional(
                        CONF_STREAM_SOURCE,
                        default=info[CONF_STREAM_SOURCE],
                    ): str,
                    vol.Optional(
                        CONF_AUTHENTICATION, default=info[CONF_AUTHENTICATION]
                    ): vol.In([HTTP_BASIC_AUTHENTICATION, HTTP_DIGEST_AUTHENTICATION]),
                    vol.Optional(CONF_USERNAME, default=info[CONF_USERNAME]): str,
                    vol.Optional(CONF_PASSWORD, default=info[CONF_PASSWORD]): str,
                    vol.Optional(
                        CONF_LIMIT_REFETCH_TO_URL_CHANGE,
                        default=info[CONF_LIMIT_REFETCH_TO_URL_CHANGE],
                    ): bool,
                    vol.Optional(
                        CONF_CONTENT_TYPE, default=info[CONF_CONTENT_TYPE]
                    ): str,
                    vol.Optional(CONF_FRAMERATE, default=info[CONF_FRAMERATE]): int,
                    vol.Optional(CONF_VERIFY_SSL, default=info[CONF_VERIFY_SSL]): bool,
                }
            ),
            errors=self._errors,
        )
