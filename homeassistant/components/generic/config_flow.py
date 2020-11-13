"""Config flow for generic (IP Camera)."""
# TODO: enabling authentication on img preview seems to cause img load to fail
# TODO: the above means we are currently exposing the preview image even to non-authenticated users.
# TODO: we should really delete the HTTP view when we've finished with it but I don't know how.

import imghdr
import logging
from typing import Any, Dict

from aiohttp import web
import av
import voluptuous as vol

from homeassistant import config_entries, data_entry_flow
from homeassistant.components.camera import DEFAULT_CONTENT_TYPE, CameraImageView
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
    CONF_EDIT_NEEDED,
    CONF_FRAMERATE,
    CONF_LIMIT_REFETCH_TO_URL_CHANGE,
    CONF_STILL_IMAGE_URL,
    CONF_STREAM_SOURCE,
    DEFAULT_NAME,
    DOMAIN,
)

SCAN_INTERVAL = 10

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
                container = av.open(info.get(CONF_STREAM_SOURCE), options=None)
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

            self.user_input = user_input
            if await self._test_connection(user_input):
                # if user_input.get(CONF_NAME) is not None:
                #     return self.async_create_entry(
                #         title=user_input[CONF_NAME], data=user_input
                #     )
                # Store the working data for the final step

                # Register a temporary view so that we can preview the image
                # at the confirmation step.
                cam = GenericCamera(self.hass, self.user_input)
                self.hass.http.register_view(CameraImagePreView(cam))
                # hass.http.register_view(CameraMjpegStream(component))

                return self.async_show_form(
                    step_id="user_confirm",
                    data_schema=vol.Schema(
                        {
                            vol.Required(CONF_NAME, default=DEFAULT_NAME): str,
                            vol.Required(CONF_EDIT_NEEDED, default=False): bool,
                        }
                    ),
                    errors=self._errors,
                )

        else:
            self.user_input = {}
            self.user_input[CONF_NAME] = DEFAULT_NAME
            self.user_input[CONF_AUTHENTICATION] = HTTP_BASIC_AUTHENTICATION
            self.user_input[CONF_LIMIT_REFETCH_TO_URL_CHANGE] = False
            self.user_input[CONF_CONTENT_TYPE] = DEFAULT_CONTENT_TYPE
            self.user_input[CONF_FRAMERATE] = 2
            self.user_input[CONF_VERIFY_SSL] = True

            user_input = {}
            user_input[CONF_NAME] = DEFAULT_NAME
            user_input[CONF_AUTHENTICATION] = HTTP_BASIC_AUTHENTICATION
            user_input[CONF_LIMIT_REFETCH_TO_URL_CHANGE] = False
            user_input[CONF_CONTENT_TYPE] = DEFAULT_CONTENT_TYPE
            user_input[CONF_FRAMERATE] = 2
            user_input[CONF_VERIFY_SSL] = True

        return self.async_show_form(
            step_id="user",
            data_schema=self.get_main_input_schema(),
            errors=self._errors,
        )

    async def async_step_user_confirm(
        self, user_input: Dict[str, Any] = None
    ) -> Dict[str, Any]:
        """Handle the confirmation step of the config flow."""
        self._errors = {}

        if user_input.get(CONF_EDIT_NEEDED, False):
            return self.async_show_form(
                step_id="user",
                data_schema=self.get_main_input_schema(),
                errors=self._errors,
            )
        if user_input is not None:
            # FIXME if there is any way to unregister the http preview we should
            # do it here e.g. self.hass.http.unregister_view(...)
            return self.async_create_entry(
                title=user_input[CONF_NAME], data=self.user_input
            )

    def get_main_input_schema(self):
        """Get the schema for user data entry."""
        return vol.Schema(
            {
                vol.Required(
                    CONF_STILL_IMAGE_URL,
                    default=self.user_input.get(CONF_STILL_IMAGE_URL),
                ): str,
                vol.Optional(
                    CONF_STREAM_SOURCE,
                    default=self.user_input.get(CONF_STREAM_SOURCE, ""),
                ): str,
                vol.Optional(
                    CONF_AUTHENTICATION,
                    default=self.user_input[CONF_AUTHENTICATION],
                ): vol.In([HTTP_BASIC_AUTHENTICATION, HTTP_DIGEST_AUTHENTICATION]),
                vol.Optional(
                    CONF_USERNAME,
                    default=self.user_input.get(CONF_USERNAME, ""),
                ): str,
                vol.Optional(
                    CONF_PASSWORD, default=self.user_input.get(CONF_PASSWORD, "")
                ): str,
                vol.Optional(
                    CONF_LIMIT_REFETCH_TO_URL_CHANGE,
                    default=self.user_input[CONF_LIMIT_REFETCH_TO_URL_CHANGE],
                ): bool,
                vol.Optional(
                    CONF_CONTENT_TYPE, default=self.user_input[CONF_CONTENT_TYPE]
                ): str,
                vol.Optional(
                    CONF_FRAMERATE, default=self.user_input[CONF_FRAMERATE]
                ): int,
                vol.Optional(
                    CONF_VERIFY_SSL, default=self.user_input[CONF_VERIFY_SSL]
                ): bool,
            }
        )


class CameraImagePreView(CameraImageView):
    """Camera view to temporarily serve an image."""

    url = "/api/camera_temp_proxy/generic_cf_camera_temp"
    name = "api:camera:imgepreview"

    def __init__(self, camera: GenericCamera) -> None:
        """Initialize a basic camera view."""
        self.camera = camera

    async def get(self, request: web.Request) -> web.Response:
        """Start a GET request."""
        camera = self.camera

        if camera is None:
            raise web.HTTPNotFound()

        # authenticated = (
        #     request[KEY_AUTHENTICATED]
        #     or request.query.get("token") in camera.access_tokens
        # )

        # if not authenticated:
        #     raise web.HTTPUnauthorized()

        if not camera.is_on:
            _LOGGER.debug("Camera is off")
            raise web.HTTPServiceUnavailable()

        return await self.handle(request, camera)
