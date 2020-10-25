"""Config flow for generic (IP Camera)."""

import imghdr
import logging
from typing import Any, Dict

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

# pylint: disable=unused-import
from .const import (
    CONF_CONTENT_TYPE,
    CONF_FRAMERATE,
    CONF_LIMIT_REFETCH_TO_URL_CHANGE,
    CONF_STILL_IMAGE_URL,
    CONF_STREAM_SOURCE,
    DEFAULT_NAME,
    DOMAIN,
)

_LOGGER = logging.getLogger(__name__)


class GenericIPCamConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Config flow for generic IP camera."""

    VERSION = 1
    CONNECTION_CLASS = config_entries.CONN_CLASS_LOCAL_POLL

    def __init__(self):
        """Initialise the config flow."""
        super().__init__()
        self._errors = {}

    async def _test_connection(self, info):
        """Verify that the camera data is valid before we add it."""
        await self.async_set_unique_id(info[CONF_STILL_IMAGE_URL])
        try:
            self._abort_if_unique_id_configured()
        except data_entry_flow.AbortFlow as err:
            if "already_configured" in str(err):
                self._errors["base"] = "still_image_already_configured"
                return False
        cam = GenericCamera(self.hass, info)
        # Minimum functionality is getting a still image
        image = await cam.async_camera_image()
        if image is None:
            self._errors["base"] = "unable_still_load"
            return False
        fmt = imghdr.what(None, h=image)
        _LOGGER.debug(
            "Still image at '%s' detected format: %s", info[CONF_STILL_IMAGE_URL], fmt
        )
        if fmt is None:
            self._errors["base"] = "invalid_still_image"
            return False

        # Second level functionality is to get a stream.
        if info.get(CONF_STREAM_SOURCE) not in [None, ""]:
            try:
                container = await self.hass.async_add_executor_job(
                    av.open, info.get(CONF_STREAM_SOURCE)
                )
                video_stream = container.streams.video[0]
                if video_stream is not None:
                    return True
            except av.error.HTTPUnauthorizedError:  # pylint: disable=c-extension-no-member
                self._errors["base"] = "stream_unauthorised"
            except (KeyError, IndexError):
                self._errors["base"] = "stream_novideo"
            except OSError as err:
                if "No route to host" in str(err):
                    self._errors["base"] = "stream_no_route_to_host"
            return False
        return True

    async def async_step_user(
        self, user_input: Dict[str, Any] = None
    ) -> Dict[str, Any]:
        """Handle the start of the config flow."""

        self._errors = {}

        if user_input is not None:
            if await self._test_connection(user_input):
                return self.async_create_entry(
                    title=user_input[CONF_NAME], data=user_input
                )
        else:
            user_input = {}
            user_input[CONF_NAME] = DEFAULT_NAME
            user_input[CONF_AUTHENTICATION] = HTTP_BASIC_AUTHENTICATION
            user_input[CONF_LIMIT_REFETCH_TO_URL_CHANGE] = False
            user_input[CONF_CONTENT_TYPE] = DEFAULT_CONTENT_TYPE
            user_input[CONF_FRAMERATE] = 2
            user_input[CONF_VERIFY_SSL] = True

        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema(
                {
                    vol.Optional(CONF_NAME, default=user_input[CONF_NAME]): str,
                    vol.Required(
                        CONF_STILL_IMAGE_URL,
                        default=user_input.get(CONF_STILL_IMAGE_URL),
                    ): str,
                    vol.Optional(
                        CONF_STREAM_SOURCE,
                        default=user_input.get(CONF_STREAM_SOURCE, ""),
                    ): str,
                    vol.Optional(
                        CONF_AUTHENTICATION, default=user_input[CONF_AUTHENTICATION]
                    ): vol.In([HTTP_BASIC_AUTHENTICATION, HTTP_DIGEST_AUTHENTICATION]),
                    vol.Optional(
                        CONF_USERNAME,
                        default=user_input.get(CONF_USERNAME, ""),
                    ): str,
                    vol.Optional(
                        CONF_PASSWORD, default=user_input.get(CONF_PASSWORD, "")
                    ): str,
                    vol.Optional(
                        CONF_LIMIT_REFETCH_TO_URL_CHANGE,
                        default=user_input[CONF_LIMIT_REFETCH_TO_URL_CHANGE],
                    ): bool,
                    vol.Optional(
                        CONF_CONTENT_TYPE, default=user_input[CONF_CONTENT_TYPE]
                    ): str,
                    vol.Optional(
                        CONF_FRAMERATE, default=user_input[CONF_FRAMERATE]
                    ): int,
                    vol.Optional(
                        CONF_VERIFY_SSL, default=user_input[CONF_VERIFY_SSL]
                    ): bool,
                }
            ),
            errors=self._errors,
        )
