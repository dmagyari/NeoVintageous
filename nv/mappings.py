# Copyright (C) 2018 The NeoVintageous Team (NeoVintageous).
#
# This file is part of NeoVintageous.
#
# NeoVintageous is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# NeoVintageous is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with NeoVintageous.  If not, see <https://www.gnu.org/licenses/>.

import logging

from NeoVintageous.nv.variables import expand_keys
from NeoVintageous.nv.vi.keys import seq_to_command
from NeoVintageous.nv.vi.keys import to_bare_command_name
from NeoVintageous.nv.vim import INSERT
from NeoVintageous.nv.vim import NORMAL
from NeoVintageous.nv.vim import OPERATOR_PENDING
from NeoVintageous.nv.vim import SELECT
from NeoVintageous.nv.vim import VISUAL
from NeoVintageous.nv.vim import VISUAL_BLOCK
from NeoVintageous.nv.vim import VISUAL_LINE

_log = logging.getLogger(__name__)

_mappings = {
    INSERT: {},
    NORMAL: {},
    OPERATOR_PENDING: {},
    SELECT: {},
    VISUAL_BLOCK: {},
    VISUAL_LINE: {},
    VISUAL: {}
}  # type: dict


class Mapping:

    def __init__(self, head, mapping, tail):
        self.mapping = mapping
        self.head = head
        self.tail = tail
        self.sequence = head + tail


def _find_partial_matches(mode, lhs):
    # type: (str, str) -> list
    return [x for x in _mappings[mode] if x.startswith(lhs)]


def _find_full_match(mode, lhs):
    if lhs in _mappings[mode]:
        return _mappings[mode][lhs]


def _normalise_lhs(lhs):
    # type: (str) -> str
    return expand_keys(lhs)


def mappings_add(mode, lhs, rhs):
    # type: (str, str, str) -> None
    _mappings[mode][_normalise_lhs(lhs)] = rhs


def mappings_remove(mode, lhs):
    # type: (str, str) -> None
    del _mappings[mode][_normalise_lhs(lhs)]


def mappings_clear():
    # type: () -> None
    for mode in _mappings:
        _mappings[mode] = {}


def _seq_to_mapping(mode, seq):
    full_match = _find_full_match(mode, seq)
    if full_match:
        return Mapping(seq, full_match, '')


def mappings_is_incomplete(mode, seq):
    # type: (str, str) -> bool
    full_match = _find_full_match(mode, seq)
    if full_match:
        return False

    partial_matches = _find_partial_matches(mode, seq)
    if partial_matches:
        return True

    return False


def mappings_resolve(state, sequence=None, mode=None, check_user_mappings=True):
    # Look at the current global state and return the command mapped to the available sequence.
    #
    # Args:
    #   sequence (str): The command sequence. If a sequence is passed, it is
    #       used instead of the global state's. This is necessary for some
    #       commands that aren't name spaces but act as them (for example,
    #       ys from the surround plugin).
    #   mode (str): If different than None, it will be used instead of the
    #       global state's. This is necessary when we are in operator
    #       pending mode and we receive a new action. By combining the
    #       existing action's name with name of the action just received we
    #       could find a new action.
    #   check_user_mappings (bool):
    #
    # Returns:
    #   Mapping:
    #   ViMissingCommandDef: If not found.

    # We usually need to look at the partial sequence, but some commands do
    # weird things, like ys, which isn't a namespace but behaves as such
    # sometimes.
    partial_sequence = state.partial_sequence
    seq = to_bare_command_name(sequence or partial_sequence)

    command = None

    if check_user_mappings:
        # TODO Review: state.mode is used instead of mode or state.mode, is it a bug?
        command = _seq_to_mapping(state.mode, seq)

    if not command:
        command = seq_to_command(state.view, seq, mode or state.mode)

    _log.debug('resolved %s %s or %s -> %s %s', mode, sequence, partial_sequence, seq, command)

    return command
