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

from collections import deque
import itertools

from sublime import get_clipboard
from sublime import set_clipboard

try:
    from Default.paste_from_history import g_clipboard_history as _clipboard_history

    def update_clipboard_history(text):
        _clipboard_history.push_text(text)

except Exception:
    print('NeoVintageous: could not import default package clipboard history updater')

    import traceback
    traceback.print_exc()

    def update_clipboard_history(text):
        print('NeoVintageous: could not update clipboard history: import error')

from NeoVintageous.nv.settings import get_setting
from NeoVintageous.nv.vim import VISUAL
from NeoVintageous.nv.vim import VISUAL_LINE
from NeoVintageous.nv.vim import is_visual_mode


# 1. The unnamed register ""
_UNNAMED = '"'

# 2. 10 numberd registers "0 to "9
_LAST_YANK = '0'
_LAST_DELETE = '1'
_NUMBERED = tuple('0123456789')

# 3 The small delete register "-
_SMALL_DELETE = '-'

# 4. 26 named registers "a to "z or "A to "Z
_NAMED = tuple('abcdefghijklmnopqrstuvwxyz')

# 5. Three read-only registers ":, "., "%
_LAST_EXECUTED_COMMAND = ':'
_LAST_INSERTED_TEXT = '.'
_CURRENT_FILE_NAME = '%'

# 6. Alternate buffer register "#
_ALTERNATE_FILE = '#'

# 7. The expression register "=
_EXPRESSION = '='

# 8. The selection and drop registers "*, "+, and "~
_CLIPBOARD_STAR = '*'
_CLIPBOARD_PLUS = '+'
_CLIPBOARD_TILDA = '~'

# 9. The black hole register "_
_BLACK_HOLE = '_'

# 10. Last search pattern register "/
_LAST_SEARCH_PATTERN = '/'

# Groups

_CLIPBOARD = (
    _CLIPBOARD_PLUS,
    _CLIPBOARD_STAR
)

_READ_ONLY = (
    _ALTERNATE_FILE,
    _CLIPBOARD_TILDA,
    _CURRENT_FILE_NAME,
    _LAST_EXECUTED_COMMAND,
    _LAST_INSERTED_TEXT
)

_SELECTION_AND_DROP = (
    _CLIPBOARD_PLUS,
    _CLIPBOARD_STAR,
    _CLIPBOARD_TILDA
)

_SPECIAL = (
    _ALTERNATE_FILE,
    _BLACK_HOLE,
    _CLIPBOARD_PLUS,
    _CLIPBOARD_STAR,
    _CLIPBOARD_TILDA,
    _CURRENT_FILE_NAME,
    _LAST_EXECUTED_COMMAND,
    _LAST_INSERTED_TEXT,
    _LAST_SEARCH_PATTERN,
    _SMALL_DELETE,
    _UNNAMED
)

_ALL = _SPECIAL + _NUMBERED + _NAMED


_data = {'0': None, '1-9': deque([None] * 9, maxlen=9)}  # type: dict
_linewise = {}  # type: dict


def _set_register_linewise(name, linewise):
    _linewise[name] = linewise


def _reset_data():
    _data.clear()
    _data['0'] = None
    _data['1-9'] = deque([None] * 9, maxlen=9)


def _shift_numbered_register(content):
    _data['1-9'].appendleft(content)


def _set_numbered_register(number, values):
    _data['1-9'][int(number) - 1] = values


def _get_numbered_register(number):
    return _data['1-9'][int(number) - 1]


def set_expression(values):
    # Coerce all values into strings.
    _data[_EXPRESSION] = [str(v) for v in values]


def _is_register_linewise(register):
    return _linewise.get(register, False)


def _is_writable_register(register):
    if register == _UNNAMED:
        return True

    if register == _SMALL_DELETE:
        return True

    if register in _CLIPBOARD:
        return True

    if register.isdigit():
        return True

    if register.isalpha():
        return True

    if register.isupper():
        return True

    if register == _EXPRESSION:
        return True

    return False


def _get(view, name=_UNNAMED):
    name = str(name)

    assert len(name) == 1, "Register names must be 1 char long."

    if name == _CURRENT_FILE_NAME:
        try:
            return [view.file_name()]
        except AttributeError:
            return ''

    if name in _CLIPBOARD:
        return [get_clipboard()]

    if ((name not in (_UNNAMED, _SMALL_DELETE)) and (name in _SPECIAL)):
        return

    # Special case lumped among these --user always wants the sys clipboard
    if ((name == _UNNAMED) and (get_setting(view, 'use_sys_clipboard') is True)):
        return [get_clipboard()]

    # If the expression register holds a value and we're requesting the unnamed
    # register, return the expression register and clear it aftwerwards.
    if name == _UNNAMED and _data.get(_EXPRESSION, ''):
        value = _data[_EXPRESSION]
        _data[_EXPRESSION] = ''

        return value

    if name.isdigit():
        if name == _LAST_YANK:
            return _data[name]

        return _get_numbered_register(name)

    try:
        return _data[name.lower()]
    except KeyError:
        pass


def registers_get(view, key):
    return _get(view, key)


def registers_get_all(view):
    return {name: _get(view, name) for name in _ALL}


def registers_get_for_paste(view, register, mode):
    if not register:
        register = _UNNAMED

    values = _get(view, register)
    linewise = _is_register_linewise(register)

    filtered = []

    if values:
        # Populate unnamed register with the text we're about to paste into (the
        # text we're about to replace), but only if there was something in
        # requested register (not empty), and we're in VISUAL mode.
        if is_visual_mode(mode):
            current_content = _get_selected_text(view, linewise=(mode == VISUAL_LINE))
            if current_content:
                _set(view, _UNNAMED, current_content, linewise=(mode == VISUAL_LINE))

        for value in values:
            if mode == VISUAL:
                if linewise and value and value[0] != '\n':
                    value = '\n' + value

            if mode == VISUAL_LINE:
                # Pasting characterwise content in visual line mode needs an
                # extra newline to account for visual line eol newline.
                if not linewise:
                    value += '\n'

            filtered.append(value)

    return filtered, linewise


# Set a register. In order to honor multiple selections in Sublime Text, we need
# to store register data as lists, one per selection. The paste command will
# then make the final decision about what to insert into the buffer when faced
# with unbalanced selection number / available register data.
def _set(view, name, values, linewise=False):
    name = str(name)

    assert len(name) == 1, "Register names must be 1 char long: " + name

    if name == _BLACK_HOLE:
        return

    if not _is_writable_register(name):
        return None  # Vim fails silently.

    assert isinstance(values, list), "Register values must be inside a list."

    values = [str(v) for v in values]

    if name.isdigit() and name != '0':
        _set_numbered_register(name, values)
    else:
        _data[name] = values
        _linewise[name] = linewise

    if name not in (_EXPRESSION,):
        _set_unnamed(values, linewise)
        _maybe_set_sys_clipboard(view, name, values)


def _append(view, name, suffixes):
    assert len(name) == 1, "Register names must be 1 char long."
    assert name in "ABCDEFGHIJKLMNOPQRSTUVWXYZ", "Can only append to A-Z registers."

    existing_values = _data.get(name.lower(), '')
    new_valuesx = itertools.zip_longest(existing_values, suffixes, fillvalue='')
    new_values = [(prefix + suffix) for (prefix, suffix) in new_valuesx]

    _data[name.lower()] = new_values

    _set_unnamed(new_values)
    _maybe_set_sys_clipboard(view, name, new_values)


def _set_unnamed(values, linewise=False):
    assert isinstance(values, list)
    _data[_UNNAMED] = [str(v) for v in values]
    _linewise[_UNNAMED] = linewise


def registers_set(view, key, value):
    try:
        if key.isupper():
            _append(view, key, value)
        else:
            _set(view, key, value)
    except AttributeError:
        # TODO [review] Looks like a bug: If set() above raises AttributeError so will this.
        _set(view, key, value)


def _maybe_set_sys_clipboard(view, name, value):
    if (name in _CLIPBOARD or get_setting(view, 'use_sys_clipboard') is True):
        value = '\n'.join(value)
        set_clipboard(value)
        update_clipboard_history(value)


def _get_selected_text(view, new_line_at_eof=False, linewise=False):
    fragments = [view.substr(r) for r in list(view.sel())]

    # Add new line at EOF, but don't add too many new lines.
    if (new_line_at_eof and not linewise):
        # XXX: It appears regions can end beyond the buffer's EOF (?).
        if (not fragments[-1].endswith('\n') and view.sel()[-1].b >= view.size()):
            fragments[-1] += '\n'

    if fragments and linewise:
        for i, f in enumerate(fragments):
            # When should we add a newline character? Always except when we have
            # a non-\n-only string followed by a newline char.
            if (not f.endswith('\n')) or f.endswith('\n\n'):
                fragments[i] = f + '\n'

    return fragments


def _op(view, operation, register=None, linewise=False):
    if register == _BLACK_HOLE:
        return

    if linewise == 'maybe':
        linewise = False
        linewise_if_multiline = True
    else:
        linewise_if_multiline = False

    selected_text = _get_selected_text(view, linewise=linewise)

    multiline = False
    for fragment in selected_text:
        if '\n' in fragment:
            multiline = True
            break

    if linewise_if_multiline and multiline:
        linewise = True

    if register and register != _UNNAMED:
        registers_set(view, register, selected_text)
    else:
        _set(view, _UNNAMED, selected_text, linewise)

        # Numbered register 0 contains the text from the most recent yank.
        if operation == 'yank':
            _set(view, _LAST_YANK, selected_text, linewise)

        # Numbered register 1 contains the text deleted by the most recent
        # delete or change command, unless the command specified another
        # register or the text is less than one line (the small delete register
        # is used then). With each successive deletion or change, Vim shifts the
        # previous contents of register 1 into register 2, 2 into 3, and so
        # forth, losing the previous contents of register 9.
        elif operation in ('change', 'delete'):
            if linewise or multiline:
                _shift_numbered_register(selected_text)
        else:
            raise ValueError('unsupported operation: ' + operation)

    # The small delete register.
    if operation in ('change', 'delete') and not multiline:
        # TODO Improve small delete register implementation.
        is_same_line = (lambda r: view.line(r.begin()) == view.line(r.end() - 1))
        if all(is_same_line(x) for x in list(view.sel())):
            _set(view, _SMALL_DELETE, selected_text, linewise)


def registers_op_change(view, register=None, linewise=False):
    _op(view, 'change', register=register, linewise=linewise)


def registers_op_delete(view, register=None, linewise=False):
    _op(view, 'delete', register=register, linewise=linewise)


def registers_op_yank(view, register=None, linewise=False):
    _op(view, 'yank', register=register, linewise=linewise)
