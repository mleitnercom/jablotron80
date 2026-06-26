import asyncio
import logging
import logging.handlers
import queue
from homeassistant.components.alarm_control_panel import (
    DOMAIN as PLATFORM_ALARM_CONTROL_PANEL,
)
from homeassistant.components.binary_sensor import DOMAIN as PLATFORM_BINARY_SENSOR
from homeassistant.components.sensor import DOMAIN as PLATFORM_SENSOR
from homeassistant.components.button import DOMAIN as PLATFORM_BUTTON
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers import device_registry as dr, config_validation as cv

# from . import hub
from .const import (
    DOMAIN,
    DATA_JABLOTRON,
    DATA_OPTIONS_UPDATE_UNSUBSCRIBER,
    NAME,
    CABLE_MODEL,
    MANUFACTURER,
    CABLE_MODELS,
)
from .jablotron import JA80CentralUnit

# List of platforms to support. There should be a matching .py file for each,
# eg <cover.py> and <sensor.py>
PLATFORMS = [
    PLATFORM_ALARM_CONTROL_PANEL,
    PLATFORM_BINARY_SENSOR,
    PLATFORM_SENSOR,
    PLATFORM_BUTTON,
]
CONFIG_SCHEMA = cv.config_entry_only_config_schema(DOMAIN)


# diagnostic: mirror jablotron logs to dedicated files on /config, since the
# HAOS journal is small (only a few minutes at DEBUG). File 1 (WARNING) is a
# long-lived store (CRC-shadow / errors), immune to the DEBUG level; file 2
# (DEBUG) is a large verbose store that only fills while DEBUG is enabled.
# Writes go through a background QueueListener so the event loop never blocks on
# disk I/O. Live-system diagnostic - not part of the upstream feature set.
def _setup_file_logging(hass: HomeAssistant) -> None:
    logger = logging.getLogger(__package__)
    if any(getattr(h, "_jablotron_file", False) for h in logger.handlers):
        return
    fmt = logging.Formatter("%(asctime)s %(levelname)s %(name)s %(message)s")
    warn_h = logging.handlers.RotatingFileHandler(
        hass.config.path("jablotron80.log"), maxBytes=50 * 1024 * 1024, backupCount=3
    )
    warn_h.setLevel(logging.WARNING)
    warn_h.setFormatter(fmt)
    debug_h = logging.handlers.RotatingFileHandler(
        hass.config.path("jablotron80.debug.log"), maxBytes=500 * 1024 * 1024, backupCount=5
    )
    debug_h.setLevel(logging.DEBUG)
    debug_h.setFormatter(fmt)
    log_queue = queue.SimpleQueue()
    queue_handler = logging.handlers.QueueHandler(log_queue)
    queue_handler.setLevel(logging.DEBUG)
    queue_handler._jablotron_file = True
    listener = logging.handlers.QueueListener(log_queue, warn_h, debug_h, respect_handler_level=True)
    listener.start()
    logger.addHandler(queue_handler)


async def async_setup(hass: HomeAssistant, config: dict):
    # Ensure our name space for storing objects is a known type. A dict is
    # common/preferred as it allows a separate instance of your class for each
    # instance that has been created in the UI.
    hass.data.setdefault(DOMAIN, {})
    await hass.async_add_executor_job(_setup_file_logging, hass)

    return True


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    # Store an instance of the "connecting" class that does the work of speaking
    # with your actual devices.
    # hass.data[DOMAIN][entry.entry_id] = hub.Hub(hass, entry.data["host"])

    # This creates each HA object for each platform your device requires.
    # It's done by calling the `async_setup_entry` function in each platform module.

    cu = JA80CentralUnit(hass, entry.data, entry.options)
    await cu.initialize()

    device_registry = dr.async_get(hass)
    device_registry.async_get_or_create(
        config_entry_id=entry.entry_id,
        identifiers={(DOMAIN, cu.serial_port)},
        name="Cable",
        model=CABLE_MODELS[entry.data[CABLE_MODEL]],
        manufacturer=MANUFACTURER,
    )

    hass.data[DOMAIN][entry.entry_id] = {
        DATA_JABLOTRON: cu,
        DATA_OPTIONS_UPDATE_UNSUBSCRIBER: entry.add_update_listener(options_update_listener),
    }

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry):
    # This is called when an entry/configured device is to be removed. The class
    # needs to unload itself, and remove callbacks. See the classes for further
    # details
    options_update_unsubscriber = hass.data[DOMAIN][entry.entry_id][DATA_OPTIONS_UPDATE_UNSUBSCRIBER]
    options_update_unsubscriber()
    cu = hass.data[DOMAIN][entry.entry_id][DATA_JABLOTRON]
    await cu.shutdown()
    hass.data[DOMAIN].pop(entry.entry_id)
    return True


async def options_update_listener(hass: HomeAssistant, entry: ConfigEntry) -> None:
    cu = hass.data[DOMAIN][entry.entry_id][DATA_JABLOTRON]
    cu.update_options(entry.options)
