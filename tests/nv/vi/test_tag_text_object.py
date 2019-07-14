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

from collections import namedtuple

from NeoVintageous.tests import unittest

from NeoVintageous.nv.vi.text_objects import find_containing_tag
from NeoVintageous.nv.vi.text_objects import get_closest_tag
from NeoVintageous.nv.vi.text_objects import get_region_end
from NeoVintageous.nv.vi.text_objects import next_end_tag
from NeoVintageous.nv.vi.text_objects import next_unbalanced_tag
from NeoVintageous.nv.vi.text_objects import previous_begin_tag

from NeoVintageous.nv.vi.text_objects import RX_ANY_TAG_NAMED_TPL


test_data = namedtuple('test_data', 'content args expected msg')


TESTS_SEARCH_TAG_FORWARD = (
    test_data(content='<a>foo', args={'start': 0}, expected=(unittest.Region(0, 3), 'a', False), msg='find tag'),
    test_data(content='<a>foo', args={'start': 1}, expected=(None, None, None), msg="don't find tag"),
    test_data(content='<a>foo</a>', args={'start': 1}, expected=(unittest.Region(6, 10), 'a', True), msg='find other tag'),  # noqa: E501
    test_data(content='<a hey="ho">foo', args={'start': 0}, expected=(unittest.Region(0, 12), 'a', False), msg='find tag with attributes'),  # noqa: E501
    test_data(content='<a hey="ho"\n>foo', args={'start': 0}, expected=(unittest.Region(0, 13), 'a', False), msg='find tag with newline between attributes'),  # noqa: E501
)

TESTS_SEARCH_TAG_BACKWARD = (
    test_data(content='<a>foo', args={'pattern': RX_ANY_TAG_NAMED_TPL.format('a'), 'start': 0, 'end': 6}, expected=(unittest.Region(0, 3), 'a', True), msg='find tag'),  # noqa: E501
    test_data(content='<a>foo', args={'pattern': RX_ANY_TAG_NAMED_TPL.format('a'), 'start': 0, 'end': 0}, expected=(None, None, None), msg="don't find tag"),  # noqa: E501
    test_data(content='</a>foo', args={'pattern': RX_ANY_TAG_NAMED_TPL.format('a'), 'start': 0, 'end': 6}, expected=(unittest.Region(0, 4), 'a', False), msg='find a closing tag'),  # noqa: E501
    test_data(content='<a>foo</a>', args={'pattern': RX_ANY_TAG_NAMED_TPL.format('a'), 'start': 0, 'end': 5}, expected=(unittest.Region(0, 3), 'a', True), msg='find other tag'),  # noqa: E501
    test_data(content='<a\they="ho">foo', args={'pattern': RX_ANY_TAG_NAMED_TPL.format('a'), 'start': 0, 'end': 14}, expected=(unittest.Region(0, 12), 'a', True), msg='find tag with attributes'),  # noqa: E501
    test_data(content='<a\nhey="ho">foo', args={'pattern': RX_ANY_TAG_NAMED_TPL.format('a'), 'start': 0, 'end': 14}, expected=(unittest.Region(0, 12), 'a', True), msg='find tag with attributes'),  # noqa: E501
)

TESTS_NEXT_UNBALANCED_END_TAG = (
    test_data(content='<p>foo <p>bar</p> baz</p>', args={'search': next_end_tag, 'search_args': {'start': 3}, 'restart_at': get_region_end}, expected=(unittest.Region(21, 25), 'p'), msg='find end tag skipping nested'),  # noqa: E501
)

TESTS_CONTAINING_TAG = (
    test_data(content='<a>foo</a>', args={'start': 4}, expected=(unittest.Region(0, 3), unittest.Region(6, 10), 'a'), msg='find tag'),  # noqa: E501
    test_data(content='<div>foo</div>', args={'start': 5}, expected=(unittest.Region(0, 5), unittest.Region(8, 14), 'div'), msg='find long tag'),  # noqa: E501
    test_data(content='<div\nclass="foo">foo</div>', args={'start': 17}, expected=(unittest.Region(0, 17), unittest.Region(20, 26), 'div'), msg='find tag with attributes'),  # noqa: E501
    test_data(content='<div>foo</div>', args={'start': 2}, expected=(unittest.Region(0, 5), unittest.Region(8, 14), 'div'), msg='find tag from within start tag'),  # noqa: E501
    test_data(content='<div>foo</div>', args={'start': 13}, expected=(unittest.Region(0, 5), unittest.Region(8, 14), 'div'), msg='find tag from within end tag'),  # noqa: E501
    test_data(content='<div>foo <p>bar</p></div>', args={'start': 12}, expected=(unittest.Region(9, 12), unittest.Region(15, 19), 'p'), msg='find nested tag from inside'),  # noqa: E501
    test_data(content='<head><link rel="shortcut icon" href="favicon.png"></head>', args={'start': 16}, expected=(unittest.Region(0, 6), unittest.Region(51, 58), 'head'), msg='find head'),  # noqa: E501
)


class TestTextObjects(unittest.ViewTestCase):

    def test_get_closest_tag(self):
        self.normal('ab')
        self.assertEqual(None, get_closest_tag(self.view, 0))
        self.assertEqual(None, get_closest_tag(self.view, 1))
        self.assertEqual(None, get_closest_tag(self.view, 2))

        self.normal('<p>x<i>ab</i></p>')
        self.assertEqual(self.Region(0, 3), get_closest_tag(self.view, 0))
        self.assertEqual(self.Region(0, 3), get_closest_tag(self.view, 1))
        self.assertEqual(self.Region(0, 3), get_closest_tag(self.view, 2))
        self.assertEqual(self.Region(0, 3), get_closest_tag(self.view, 3))
        self.assertEqual(self.Region(4, 7), get_closest_tag(self.view, 4))
        self.assertEqual(self.Region(4, 7), get_closest_tag(self.view, 5))
        self.assertEqual(self.Region(4, 7), get_closest_tag(self.view, 6))
        self.assertEqual(self.Region(4, 7), get_closest_tag(self.view, 7))
        self.assertEqual(self.Region(4, 7), get_closest_tag(self.view, 8))
        self.assertEqual(self.Region(9, 13), get_closest_tag(self.view, 9))


class Test_next_unbalanced_end_tag(unittest.ViewTestCase):

    def test_next_unbalanced_end_tag(self):
        self.view.set_syntax_file('Packages/HTML/HTML.tmLanguage')
        for (i, data) in enumerate(TESTS_NEXT_UNBALANCED_END_TAG):
            self.write(data.content)
            actual = next_unbalanced_tag(self.view, **data.args)

            msg = "failed at test index {0}: {1}".format(i, data.msg)
            self.assertEqual(data.expected, actual, msg)


class Test_TagSearch(unittest.ViewTestCase):

    def test_next_end_tag(self):
        self.view.set_syntax_file('Packages/HTML/HTML.tmLanguage')
        for (i, data) in enumerate(TESTS_SEARCH_TAG_FORWARD):
            self.write(data.content)
            actual = next_end_tag(self.view, **data.args)

            msg = "failed at test index {0}: {1}".format(i, data.msg)
            self.assertEqual(data.expected, actual, msg)

    def test_previous_begin_tag(self):
        self.view.set_syntax_file('Packages/HTML/HTML.tmLanguage')
        for (i, data) in enumerate(TESTS_SEARCH_TAG_BACKWARD):
            self.write(data.content)
            actual = previous_begin_tag(self.view, **data.args)

            msg = "failed at test index {0}: {1}".format(i, data.msg)
            self.assertEqual(data.expected, actual, msg)


class Test_FindContainingTag(unittest.ViewTestCase):

    def test_find_containing_tag(self):
        self.view.set_syntax_file('Packages/HTML/HTML.tmLanguage')
        for (i, data) in enumerate(TESTS_CONTAINING_TAG):
            self.write(data.content)
            actual = find_containing_tag(self.view, **data.args)

            msg = "failed at test index {0}: {1}".format(i, data.msg)
            self.assertEqual(data.expected, actual, msg)
