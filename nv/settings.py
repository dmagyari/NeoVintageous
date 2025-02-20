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

from sublime import load_settings
from sublime import save_settings


def get_setting(view, name, default=None):
    return view.settings().get('vintageous_%s' % name, default)


def set_setting(view, name, value):
    view.settings().set('vintageous_%s' % name)


def reset_setting(view, name):
    view.settings().erase('vintageous_%s' % name)


def _get_private(obj, name, default=None):
    return obj.settings().get('_vintageous_%s' % name, default)


def _set_private(obj, name, value):
    obj.settings().set('_vintageous_%s' % name, value)


# DEPRECATED Refactor to use get_setting() instead
def get_setting_neo(view, name):
    return view.settings().get('neovintageous_%s' % name)


def get_last_char_search(view):
    # The last characte used for searches such as "f" and "t".
    return _get_private(view.window(), 'last_char_search', '')


def get_last_char_search_command(view):
    # Supports repeating the last search commands. For example the command ";"
    # (semi-colon) repeats the latest f, t, F or T [count] times and "," (comma)
    # repeats the latest f, t, F or T in opposite direction [count] times.
    return _get_private(view.window(), 'last_char_search_command', 'vi_f')


def set_last_char_search(view, value):
    _set_private(view.window(), 'last_char_search', value)


def set_last_char_search_command(view, value):
    _set_private(view.window(), 'last_char_search_command', value)


def get_last_buffer_search(view):
    # The last characte used for searches such as "/" and "?".
    return _get_private(view.window(), 'last_buffer_search', '')


def get_last_buffer_search_command(view):
    # Supports repeating the last search commands. For example the command "n".
    return _get_private(view.window(), 'last_buffer_search_command', 'vi_slash')


def set_last_buffer_search(view, value):
    _set_private(view.window(), 'last_buffer_search', value)


def set_last_buffer_search_command(view, value):
    _set_private(view.window(), 'last_buffer_search_command', value)


def get_reset_during_init(view):
    # Some commands gather input through input panels. An input panel is a view,
    # but when it's closed, the previous view gets activated and init code runs.
    # This setting can be used to inhibit running the init code when activated.
    return _get_private(view.window(), 'reset_during_init', True)


def set_reset_during_init(view, value):
    _set_private(view.window(), 'reset_during_init', value)


def _toggle_preference(name):
    preferences = load_settings('Preferences.sublime-settings')
    value = preferences.get(name)
    preferences.set(name, not value)
    save_settings('Preferences.sublime-settings')


def toggle_ctrl_keys():
    _toggle_preference('vintageous_use_ctrl_keys')


def toggle_super_keys():
    _toggle_preference('vintageous_use_super_keys')


def toggle_side_bar(window):
    window.run_command('toggle_side_bar')

    if window.is_sidebar_visible():
        window.run_command('focus_side_bar')
    else:
        window.focus_group(window.active_group())
