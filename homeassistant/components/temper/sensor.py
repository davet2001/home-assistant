"""Support for getting temperature from TEMPer devices."""
import logging
import voluptuous as vol

from homeassistant.components.sensor import PLATFORM_SCHEMA
from homeassistant.const import CONF_NAME, DEVICE_DEFAULT_NAME, \
                TEMP_FAHRENHEIT, TEMP_CELSIUS, DEVICE_CLASS_TEMPERATURE, \
                DEVICE_CLASS_HUMIDITY
from homeassistant.helpers.entity import Entity

_LOGGER = logging.getLogger(__name__)

CONF_SCALE = "scale"
CONF_OFFSET = "offset"

PLATFORM_SCHEMA = PLATFORM_SCHEMA.extend(
    {
        vol.Optional(CONF_NAME, default=DEVICE_DEFAULT_NAME): vol.Coerce(str),
        vol.Optional(CONF_SCALE, default=1): vol.Coerce(float),
        vol.Optional(CONF_OFFSET, default=0): vol.Coerce(float),
    }
)


TEMPER_SENSORS = []


def get_temper_devices():
    """Scan the Temper devices from temperusb."""
    from temperusb.temper import TemperHandler

    return TemperHandler().get_devices()


def setup_platform(hass, config, add_entities, discovery_info=None):
    """Set up the Temper sensors."""
    temp_unit = hass.config.units.temperature_unit
    name = config.get(CONF_NAME)
    scaling = {"scale": config.get(CONF_SCALE), "offset": config.get(CONF_OFFSET)}
    temper_devices = get_temper_devices()

    for idx, dev in enumerate(temper_devices):
        if idx != 0:
            name = name + '_' + str(idx)
        _LOGGER.debug("adding sensor...")
        TEMPER_SENSORS.append(TemperSensor(dev, temp_unit, DEVICE_CLASS_TEMPERATURE, name, scaling))
        if dev.lookup_humidity_offset(0) != None:
            _LOGGER.debug("adding humidity sensor...")
            TEMPER_SENSORS.append(TemperSensor(dev, "%", DEVICE_CLASS_HUMIDITY, 
                    name + "_RH", {'scale': 1.0, 'offset': 0.0}))
    add_entities(TEMPER_SENSORS)


def reset_devices():
    """
    Re-scan for underlying Temper sensors and assign them to our devices.

    This assumes the same sensor devices are present in the same order.
    """
    temper_devices = get_temper_devices()
    for sensor, device in zip(TEMPER_SENSORS, temper_devices):
        sensor.set_temper_device(device)


class TemperSensor(Entity):
    """Representation of a Temper temperature sensor."""

    def __init__(self, temper_device, unit_of_measurement, device_class, name, scaling):
        """Initialize the sensor."""
        self.unit_of_meas = unit_of_measurement
        self.device_clas = device_class
        self.scale = scaling['scale']
        self.offset = scaling['offset']
        self.current_value = None
        self._name = name
        self.set_temper_device(temper_device)

    @property
    def name(self):
        """Return the name of the temperature sensor."""
        return self._name

    @property
    def state(self):
        """Return the state of the entity."""
        return self.current_value

    @property
    def unit_of_measurement(self):
        """Return the unit of measurement of this entity, if any."""
        return self.unit_of_meas

    @property
    def device_class(self):
        """Return the unit of measurement of this entity, if any."""
        return self.device_clas

    def set_temper_device(self, temper_device):
        """Assign the underlying device for this sensor."""
        self.temper_device = temper_device

        # set calibration data
        self.temper_device.set_calibration_data(scale=self.scale, offset=self.offset)

    def update(self):
        """Retrieve latest state."""
        try:
            if self.device_class == DEVICE_CLASS_TEMPERATURE:
                if self.unit_of_meas == TEMP_FAHRENHEIT:
                    format_str = 'fahrenheit'
                elif self.unit_of_meas == TEMP_CELSIUS:
                    format_str = 'celsius'
                sensor_value = self.temper_device.get_temperature(format_str)
                self.current_value = round(sensor_value, 1)
            elif self.device_class == DEVICE_CLASS_HUMIDITY:
                sensor_value = self.temper_device.get_humidity()[0]['humidity_pc']
                self.current_value = round(sensor_value, 1)
        except IOError:
            _LOGGER.error("Failed to get reading. The device address may"
                          "have changed. Attempting to reset device")
            reset_devices()
