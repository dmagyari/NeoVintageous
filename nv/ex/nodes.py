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

from sublime import Region

from NeoVintageous.nv.ex.tokens import TokenDigits
from NeoVintageous.nv.ex.tokens import TokenDollar
from NeoVintageous.nv.ex.tokens import TokenDot
from NeoVintageous.nv.ex.tokens import TokenMark
from NeoVintageous.nv.ex.tokens import TokenOfSearch
from NeoVintageous.nv.ex.tokens import TokenOffset
from NeoVintageous.nv.ex.tokens import TokenPercent
from NeoVintageous.nv.ex.tokens import TokenSearchBackward
from NeoVintageous.nv.ex.tokens import TokenSearchForward
from NeoVintageous.nv.marks import get_mark_as_encoded_address
from NeoVintageous.nv.utils import row_at
from NeoVintageous.nv.vi.search import reverse_search_by_pt


class Node:
    pass


def _resolve_line_number(view, token, current):
    # type: (...) -> int
    # Args:
    #   view (View): The view where the calculation is made.
    #   token (Token):
    #   current (int): Line number where we are now.
    if isinstance(token, TokenDot):
        return row_at(view, view.text_point(current, 0))

    if isinstance(token, TokenDigits):
        return max(int(token.content) - 1, -1)

    if isinstance(token, TokenPercent):
        return row_at(view, view.size())

    if isinstance(token, TokenDollar):
        return row_at(view, view.size())

    if isinstance(token, TokenOffset):
        return current + sum(token.content)

    if isinstance(token, TokenSearchForward):
        match = view.find(token.content, view.text_point(current, 0))
        if not match:
            raise ValueError('pattern not found')

        return row_at(view, match.a)

    if isinstance(token, TokenSearchBackward):
        match = reverse_search_by_pt(view, token.content, 0, view.text_point(current, 0))
        if not match:
            raise ValueError('pattern not found')

        return row_at(view, match.a)

    if isinstance(token, TokenMark):
        if token.content == '<':
            sel = list(view.sel())[0]
            view.sel().clear()
            view.sel().add(sel)
            if sel.a < sel.b:
                return row_at(view, sel.a)
            else:
                return row_at(view, sel.a - 1)
        elif token.content == '>':
            sel = list(view.sel())[0]
            view.sel().clear()
            view.sel().add(sel)
            if sel.a < sel.b:
                return row_at(view, sel.b - 1)
            else:
                return row_at(view, sel.b)
        elif token.content in tuple('abcdefghijklmnopqrstuvwxyz'):
            return view.rowcol(get_mark_as_encoded_address(view, token.content).b)[0]

    raise NotImplementedError()


def _resolve_line_reference(view, line_reference, current=0):
    # type: (...) -> int
    # Args:
    #   view (View): The view where the calculation is made.
    #   line_reference (list): The sequence of tokens defining the line range to be calculated.
    #   current (int): Line number where we are now.
    last_token = None
    # XXX: what happens if there is no selection in the view?
    current = row_at(view, view.sel()[0].b)
    for token in line_reference:
        # Make sure a search forward doesn't overlap with
        # a match obtained right before this search.
        if isinstance(last_token, TokenOfSearch) and isinstance(token, TokenOfSearch):
            if isinstance(token, TokenSearchForward):
                current += 1

        current = _resolve_line_number(view, token, current)

        last_token = token

    return current


class RangeNode(Node):

    # Represents a Vim line range.

    def __init__(self, start=None, end=None, separator=None):
        # Args:
        #   start (list[Token]):
        #   end (list[Token]):
        #   separator (Token):
        self.start = start or []
        self.end = end or []
        self.separator = separator

    def __str__(self):
        return '{}{}{}'.format(
            ' '.join(str(x) for x in self.start),
            str(self.separator) if self.separator else '',
            ' '.join(str(x) for x in self.end),
        )

    def __eq__(self, other):
        if not isinstance(other, RangeNode):
            return False

        return (self.start == other.start and
                self.end == other.end and
                self.separator == other.separator)

    @property
    def is_empty(self):
        # type: () -> bool

        # Indicate whether this range has ever been defined. For example, in
        # interactive mode, if `true`, it means that the user hasn't provided
        # any line range on the command line.

        return not any((self.start, self.end, self.separator))

    def resolve(self, view):
        # type: (...) -> Region

        # Return a representing the Vim line range that the ex command should
        # operate on.

        start = _resolve_line_reference(view, self.start or [TokenDot()])

        if not self.separator:
            if start == -1:
                return Region(-1, -1)

            if len(self.start) == 1 and isinstance(self.start[0], TokenPercent):
                return Region(0, view.size())

            return view.full_line(view.text_point(start, 0))

        new_start = start if self.separator == ';' else 0
        end = _resolve_line_reference(view, self.end or [TokenDot()], current=new_start)

        return view.full_line(Region(view.text_point(start, 0), view.text_point(end, 0)))


class CommandLineNode(Node):

    def __init__(self, line_range, command):
        # Args:
        #   :line_range (RangeNode):
        #   :command (TokenCommand):
        self.line_range = line_range
        self.command = command

    def __str__(self):
        return '{}{}'.format(str(self.line_range), str(self.command) if self.command else '')

    def validate(self):
        # type: () -> None
        if not (self.command and self.line_range):
            return

        if not self.command.addressable and not self.line_range.is_empty:
            raise Exception("E481: No range allowed")
