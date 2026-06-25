"""Tests for the per-code "last used" timestamp (issue #83).

Each code records a wall-clock timestamp whenever it is used (arm/disarm), and
the code entities surface it as a non-breaking ``last_used`` attribute alongside
the existing active/inactive state. This mirrors the detector
``last_reported_active`` pattern.

Stub note: like ``tests/test_battery.py``, importing ``jablotronHA`` pulls in
extra Home Assistant helper modules that the shared conftest does not stub, so
we provide the few needed symbols locally before importing ``JablotronEntity``.
"""

import datetime
import sys
import types

import custom_components.jablotron80.jablotron as jablotron
from custom_components.jablotron80.jablotron import JablotronCode
from custom_components.jablotron80.const import (
    CABLE_MODEL,
    CABLE_MODEL_JA82T,
    CONFIGURATION_PASSWORD,
    CONFIGURATION_SERIAL_PORT,
)


def _ensure_module(name: str) -> types.ModuleType:
    mod = sys.modules.get(name)
    if mod is None:
        mod = types.ModuleType(name)
        sys.modules[name] = mod
    return mod


_entity = _ensure_module("homeassistant.helpers.entity")
if not hasattr(_entity, "Entity"):

    class Entity:  # noqa: D401 - dummy stand-in
        """Minimal Entity stand-in."""

    _entity.Entity = Entity

_typing = _ensure_module("homeassistant.helpers.typing")
if not hasattr(_typing, "StateType"):
    _typing.StateType = object

_restore = _ensure_module("homeassistant.helpers.restore_state")
if not hasattr(_restore, "RestoreEntity"):

    class RestoreEntity:  # noqa: D401 - dummy stand-in
        """Minimal RestoreEntity stand-in."""

    _restore.RestoreEntity = RestoreEntity

_dispatcher = _ensure_module("homeassistant.helpers.dispatcher")
if not hasattr(_dispatcher, "async_dispatcher_connect"):
    _dispatcher.async_dispatcher_connect = lambda *a, **k: None

from custom_components.jablotron80.jablotronHA import JablotronEntity  # noqa: E402

# Internal code id 1 (panel source 0x41): a user code, not the admin code (id 0).
CODE_ID = 1


def _build_unit():
    config = {
        CABLE_MODEL: CABLE_MODEL_JA82T,
        CONFIGURATION_SERIAL_PORT: "/dev/null",
        CONFIGURATION_PASSWORD: "1234",
    }
    return jablotron.JA80CentralUnit(hass=None, config=config, options=None)


def test_activate_code_records_last_used(event_loop_for_setters):
    """Using a code records a recent tz-aware wall-clock timestamp."""
    unit = _build_unit()
    code = unit.get_code(CODE_ID)
    assert isinstance(code, JablotronCode)

    before = datetime.datetime.now(datetime.timezone.utc)
    unit._activate_code_object(code)
    after = datetime.datetime.now(datetime.timezone.utc)

    assert code.active is True
    assert CODE_ID in unit._code_last_used_wall
    ts = unit._code_last_used_wall[CODE_ID]
    assert isinstance(ts, datetime.datetime)
    assert ts.tzinfo is not None
    assert before <= ts <= after


def test_code_entity_exposes_last_used(event_loop_for_setters):
    """A used code exposes the last_used attribute equal to the recorded time."""
    unit = _build_unit()
    code = unit.get_code(CODE_ID)
    unit._activate_code_object(code)

    attr = JablotronEntity(unit, code).extra_state_attributes
    assert "last_used" in attr
    assert attr["last_used"] == unit._code_last_used_wall[CODE_ID]


def test_unused_code_has_no_last_used(event_loop_for_setters):
    """A code that has never been used exposes no last_used attribute."""
    unit = _build_unit()
    code = unit.get_code(CODE_ID)  # created but never activated

    attr = JablotronEntity(unit, code).extra_state_attributes
    assert "last_used" not in attr
