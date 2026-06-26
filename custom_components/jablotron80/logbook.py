"""Logbook descriptions for jablotron80 events.

#83/#98 follow-up: render the ``jablotron_code_used`` event as a logbook entry,
linked to the code's ``binary_sensor`` entity so each code gets its own usage
history (alongside the ``last_used`` attribute). Home Assistant's logbook
integration auto-discovers this platform and calls ``async_describe_events``.
"""

from homeassistant.components.logbook import (
    LOGBOOK_ENTRY_ENTITY_ID,
    LOGBOOK_ENTRY_MESSAGE,
    LOGBOOK_ENTRY_NAME,
)
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers import entity_registry as er

from .const import DOMAIN, EVENT_CODE_USED


@callback
def async_describe_events(hass: HomeAssistant, async_describe_event) -> None:
    """Describe jablotron80 logbook events."""

    @callback
    def async_describe_code_used(event):
        data = event.data
        entity_id = None
        unique_id = data.get("unique_id")
        if unique_id:
            # The code is exposed as a binary_sensor; resolve its entity so the
            # entry shows in that code's activity, not just the global logbook.
            entity_id = er.async_get(hass).async_get_entity_id("binary_sensor", DOMAIN, unique_id)
        return {
            LOGBOOK_ENTRY_NAME: data.get("name") or "Code",
            LOGBOOK_ENTRY_MESSAGE: "was used",
            LOGBOOK_ENTRY_ENTITY_ID: entity_id,
        }

    async_describe_event(DOMAIN, EVENT_CODE_USED, async_describe_code_used)
