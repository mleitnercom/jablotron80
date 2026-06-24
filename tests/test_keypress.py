"""Tests for ``JablotronKeyPress.get_beep_option`` - relates to upstream issue #44.

``JablotronKeyPress._BEEP_OPTIONS`` maps a numeric beep code to a description.
The defined keys are 0,1,2,3,4,5,7,8 and 0xE (14). Notably **key 6 is missing**.

Issue #44 reports a ``KeyError: 6`` raised from ``get_beep_option(6)`` because the
central unit can emit beep code 6 but the lookup dict has no entry for it. These
tests:

1. document the values returned for the defined keys, and
2. capture the current (buggy) behaviour for the missing key 6 via
   ``pytest.raises(KeyError)`` so the gap is recorded.

Per the task, jablotron.py is intentionally NOT modified here - the test only
captures the behaviour.
"""

import pytest

import custom_components.jablotron80.jablotron as jablotron

JablotronKeyPress = jablotron.JablotronKeyPress


# ---------------------------------------------------------------------------
# Defined beep codes return their mapped value/description.
# ---------------------------------------------------------------------------
def test_get_beep_option_returns_defined_values():
    assert JablotronKeyPress.get_beep_option(0x0)["val"] == "1s"
    assert JablotronKeyPress.get_beep_option(0x1)["val"] == "1l"
    assert JablotronKeyPress.get_beep_option(0x2)["val"] == "2l"
    assert JablotronKeyPress.get_beep_option(0x3)["val"] == "3l"
    assert JablotronKeyPress.get_beep_option(0x4)["val"] == "4s"
    assert JablotronKeyPress.get_beep_option(0x5)["val"] == "3s"
    assert JablotronKeyPress.get_beep_option(0x7)["val"] == "0(1)"
    assert JablotronKeyPress.get_beep_option(0x8)["val"] == "0(2)"
    assert JablotronKeyPress.get_beep_option(0xE)["val"] == "?"


def test_get_beep_option_returns_dict_with_description():
    option = JablotronKeyPress.get_beep_option(0x0)
    assert set(option.keys()) == {"val", "desc"}
    assert "beep" in option["desc"].lower()


# ---------------------------------------------------------------------------
# Issue #44: beep code 6 is not in the table -> KeyError.
# This documents (does not fix) the gap.
# ---------------------------------------------------------------------------
def test_get_beep_option_6_raises_keyerror_issue_44():
    """Capture upstream issue #44: get_beep_option(6) raises KeyError: 6.

    Beep code 6 is not present in ``_BEEP_OPTIONS`` (defined keys are
    0,1,2,3,4,5,7,8,14). This asserts the *current* behaviour. If issue #44 is
    later fixed by adding key 6, this test will start failing and should be
    updated to assert the new mapped value instead.
    """
    assert 6 not in JablotronKeyPress._BEEP_OPTIONS  # precondition for the bug
    with pytest.raises(KeyError):
        JablotronKeyPress.get_beep_option(6)


# ---------------------------------------------------------------------------
# A small contrasting check on the keypress map (a sibling lookup that *is*
# complete for the codes it covers), to show the helper otherwise works.
# ---------------------------------------------------------------------------
def test_get_keypress_option_known_codes():
    assert JablotronKeyPress.get_keypress_option(0x0)["val"] == "0"
    assert JablotronKeyPress.get_keypress_option(0xE)["val"] == "#"  # ESC/OFF
    assert JablotronKeyPress.get_keypress_option(0xF)["val"] == "*"  # ON
