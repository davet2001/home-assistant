"""Test The generic (IP Camera) config flow."""

from io import BytesIO

from PIL import Image
import av

from homeassistant import config_entries, data_entry_flow, setup
import homeassistant.components.generic
from homeassistant.components.generic.const import (
    CONF_CONTENT_TYPE,
    CONF_FRAMERATE,
    CONF_LIMIT_REFETCH_TO_URL_CHANGE,
    CONF_STILL_IMAGE_URL,
    CONF_STREAM_SOURCE,
    DOMAIN,
)
from homeassistant.const import (
    CONF_AUTHENTICATION,
    CONF_NAME,
    CONF_PASSWORD,
    CONF_USERNAME,
    CONF_VERIFY_SSL,
    HTTP_BASIC_AUTHENTICATION,
)

from tests.async_mock import Mock, patch
from tests.common import MockConfigEntry

TESTDATA = {
    CONF_NAME: "cam1",
    CONF_STILL_IMAGE_URL: "http://127.0.0.1/testurl/1",
    CONF_STREAM_SOURCE: "http://127.0.0.2/testurl/2",
    CONF_AUTHENTICATION: HTTP_BASIC_AUTHENTICATION,
    CONF_USERNAME: "fred_flintstone",
    CONF_PASSWORD: "bambam",
    CONF_LIMIT_REFETCH_TO_URL_CHANGE: False,
    CONF_CONTENT_TYPE: "image/jpeg",
    CONF_FRAMERATE: 5,
    CONF_VERIFY_SSL: False,
}

buf = BytesIO()  # fake image in ram for testing.
Image.new("RGB", (1, 1)).save(buf, format="PNG")
fakeimgbytes = bytes(buf.getbuffer())

fakevidcontainer = Mock()  # fake container object with .streams.video[0] != None
fakevidcontainer.streams.video = ["fakevid"]


async def test_form(hass):
    """Test we get the form."""
    await setup.async_setup_component(hass, "persistent_notification", {})
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )
    assert result["type"] == "form"
    assert result["errors"] == {}

    with patch(
        "homeassistant.components.generic.camera.GenericCamera.async_camera_image",
        return_value=fakeimgbytes,
    ), patch("av.open", return_value=fakevidcontainer) as mock_setup:
        result2 = await hass.config_entries.flow.async_configure(
            result["flow_id"],
            TESTDATA,
        )
    assert result2["type"] == data_entry_flow.RESULT_TYPE_CREATE_ENTRY
    assert result2["title"] == "cam1"
    assert result2["data"] == {
        CONF_NAME: "cam1",
        CONF_STILL_IMAGE_URL: "http://127.0.0.1/testurl/1",
        CONF_STREAM_SOURCE: "http://127.0.0.2/testurl/2",
        CONF_AUTHENTICATION: HTTP_BASIC_AUTHENTICATION,
        CONF_USERNAME: "fred_flintstone",
        CONF_PASSWORD: "bambam",
        CONF_LIMIT_REFETCH_TO_URL_CHANGE: False,
        CONF_CONTENT_TYPE: "image/jpeg",
        CONF_FRAMERATE: 5,
        CONF_VERIFY_SSL: False,
    }

    await hass.async_block_till_done()
    assert len(mock_setup.mock_calls) == 1


async def test_form_only_stillimage(hass):
    """Test we complete ok if the user wants still images only."""
    await setup.async_setup_component(hass, "persistent_notification", {})
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )
    assert result["type"] == "form"
    assert result["errors"] == {}

    with patch(
        "homeassistant.components.generic.camera.GenericCamera.async_camera_image",
        return_value=fakeimgbytes,
    ) as mock_setup:
        result2 = await hass.config_entries.flow.async_configure(
            result["flow_id"],
            {
                CONF_NAME: "cam1",
                CONF_STILL_IMAGE_URL: "http://127.0.0.1/testurl/1",
                CONF_AUTHENTICATION: HTTP_BASIC_AUTHENTICATION,
                CONF_USERNAME: "fred_flintstone",
                CONF_PASSWORD: "bambam",
                CONF_LIMIT_REFETCH_TO_URL_CHANGE: False,
                CONF_CONTENT_TYPE: "image/jpeg",
                CONF_FRAMERATE: 5,
                CONF_VERIFY_SSL: False,
            },
        )
    assert result2["type"] == data_entry_flow.RESULT_TYPE_CREATE_ENTRY
    assert result2["title"] == "cam1"
    assert result2["data"] == {
        CONF_NAME: "cam1",
        CONF_STILL_IMAGE_URL: "http://127.0.0.1/testurl/1",
        CONF_AUTHENTICATION: HTTP_BASIC_AUTHENTICATION,
        CONF_STREAM_SOURCE: "",
        CONF_USERNAME: "fred_flintstone",
        CONF_PASSWORD: "bambam",
        CONF_LIMIT_REFETCH_TO_URL_CHANGE: False,
        CONF_CONTENT_TYPE: "image/jpeg",
        CONF_FRAMERATE: 5,
        CONF_VERIFY_SSL: False,
    }

    await hass.async_block_till_done()
    assert len(mock_setup.mock_calls) == 1


async def test_form_already_configured(hass):
    """Test we handle no route to host."""
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )

    with patch(
        "homeassistant.config_entries.ConfigFlow._abort_if_unique_id_configured",
        side_effect=data_entry_flow.AbortFlow("already_configured"),
    ):
        result2 = await hass.config_entries.flow.async_configure(
            result["flow_id"],
            TESTDATA,
        )
    assert result2["type"] == "form"
    assert result2["errors"] == {"base": "still_image_already_configured"}


async def test_form_stream_noimage(hass):
    """Test we handle no image from stream."""
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )
    with patch(
        "homeassistant.components.generic.camera.GenericCamera.async_camera_image",
        return_value=fakeimgbytes,
    ), patch("imghdr.what", return_value=None):
        result2 = await hass.config_entries.flow.async_configure(
            result["flow_id"],
            TESTDATA,
        )

    assert result2["type"] == "form"
    assert result2["errors"] == {"base": "invalid_still_image"}


async def test_form_stream_invalidimage(hass):
    """Test we handle no image from stream."""
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )
    with patch(
        "homeassistant.components.generic.camera.GenericCamera.async_camera_image",
        return_value=None,
    ):
        result2 = await hass.config_entries.flow.async_configure(
            result["flow_id"],
            TESTDATA,
        )

    assert result2["type"] == "form"
    assert result2["errors"] == {"base": "unable_still_load"}


async def test_form_stream_unauthorised(hass):
    """Test we handle invalid auth."""
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )

    with patch(
        "homeassistant.components.generic.camera.GenericCamera.async_camera_image",
        return_value=fakeimgbytes,
    ), patch("av.open", side_effect=av.error.HTTPUnauthorizedError(0, 0)):
        result2 = await hass.config_entries.flow.async_configure(
            result["flow_id"],
            TESTDATA,
        )
    assert result2["type"] == "form"
    assert result2["errors"] == {"base": "stream_unauthorised"}


async def test_form_stream_novideo(hass):
    """Test we handlen invalid stream."""
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )

    with patch(
        "homeassistant.components.generic.camera.GenericCamera.async_camera_image",
        return_value=fakeimgbytes,
    ), patch("av.open", side_effect=KeyError()):
        result2 = await hass.config_entries.flow.async_configure(
            result["flow_id"],
            TESTDATA,
        )
    assert result2["type"] == "form"
    assert result2["errors"] == {"base": "stream_novideo"}


async def test_form_no_route_to_host(hass):
    """Test we handle no route to host."""
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )

    with patch(
        "homeassistant.components.generic.camera.GenericCamera.async_camera_image",
        return_value=fakeimgbytes,
    ), patch("av.open", side_effect=OSError("No route to host")):
        result2 = await hass.config_entries.flow.async_configure(
            result["flow_id"],
            TESTDATA,
        )
    assert result2["type"] == "form"
    assert result2["errors"] == {"base": "stream_no_route_to_host"}


async def test_unload_entry(hass):
    """Test unloading the generic IP Camera entry."""

    await setup.async_setup_component(hass, "persistent_notification", {})
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )
    assert result["type"] == "form"
    assert result["errors"] == {}

    with patch(
        "homeassistant.components.generic.camera.GenericCamera.async_camera_image",
        return_value=fakeimgbytes,
    ), patch("av.open", return_value=fakevidcontainer):
        mock_entry = MockConfigEntry(
            domain=DOMAIN,
            data={
                CONF_NAME: "cam1",
                CONF_STILL_IMAGE_URL: "http://127.0.0.1/testurl/1",
                CONF_STREAM_SOURCE: "http://127.0.0.2/testurl/2",
                CONF_AUTHENTICATION: HTTP_BASIC_AUTHENTICATION,
                CONF_USERNAME: "fred_flintstone",
                CONF_PASSWORD: "bambam",
                CONF_LIMIT_REFETCH_TO_URL_CHANGE: False,
                CONF_CONTENT_TYPE: "image/jpeg",
                CONF_FRAMERATE: 5,
                CONF_VERIFY_SSL: False,
            },
        )
        mock_entry.add_to_hass(hass)
        assert await homeassistant.components.generic.async_setup_entry(
            hass, mock_entry
        )
        await hass.async_block_till_done()
        assert await hass.config_entries.async_unload(mock_entry.entry_id)
        await hass.async_block_till_done()
