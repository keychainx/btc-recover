#!/usr/bin/python
# -*- coding: utf-8 -*-

# test-btcr.py -- unit tests for btcrecovery.py
# Copyright (C) 2014, 2015 Christopher Gurnee
#
# This file is part of btcrecover.
#
# btcrecover is free software: you can redistribute it and/or
# modify it under the terms of the GNU General Public License
# as published by the Free Software Foundation; either version
# 2 of the License, or (at your option) any later version.
#
# btcrecover is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see http://www.gnu.org/licenses/

# If you find this program helpful, please consider a small
# donation to the developer at the following Bitcoin address:
#
#           17LGpN2z62zp7RS825jXwYtE7zZ19Mxxu8
#
#                      Thank You!

# (all futures as of 2.6 and 2.7 except unicode_literals)
from __future__ import print_function, absolute_import, division, \
                       generators, nested_scopes, with_statement

# Uncomment for Unicode support (and comment out the next block)
#from __future__ import unicode_literals
#import btcrecoveru as btcrecover, io
#StringIOSubclassable = io.StringIO
#BytesIO  = io.BytesIO
#StringIO = io.StringIO
#tstr = unicode
#tchr = unichr

# Uncomment for ASCII-only support (and comment out the previous block)
import btcrecover, StringIO, cStringIO
StringIOSubclassable = StringIO.StringIO
BytesIO  = StringIO.StringIO
StringIO = cStringIO.StringIO
tstr = str
tchr = chr

import warnings
# Convert warnings to errors:
warnings.simplefilter("error")
# except this from Intel's OpenCL compiler:
warnings.filterwarnings("ignore", r"Non-empty compiler output encountered\. Set the environment variable PYOPENCL_COMPILER_OUTPUT=1 to see more\.", UserWarning)
# and except this from Armory:
warnings.filterwarnings("ignore", r"the sha module is deprecated; use the hashlib module instead", DeprecationWarning)

import unittest, os, cPickle, tempfile, shutil, filecmp, sys

wallet_dir = os.path.join(os.path.dirname(__file__), "test-wallets")
typos_dir  = os.path.join(os.path.dirname(__file__), "typos")


class NonClosingBase(object):
    pass

class StringIONonClosing(StringIOSubclassable, NonClosingBase):
    def close(self): pass

class BytesIONonClosing(BytesIO, NonClosingBase):
    def close(self): pass

class GeneratorTester(unittest.TestCase):

    # tokenlist == a list of lines (w/o "\n") which will become the tokenlist file
    # expected_passwords == a list of passwords which should be produced from the tokenlist
    # extra_cmd_line == a single string of additional command-line options
    # test_passwordlist == whether or not to also test --passwordlist
    # chunksize == the password generator chunksize
    # expected_skipped == the expected # of skipped passwords, if any
    # extra_kwds == additional StringIO objects to act as file stand-ins
    def do_generator_test(self, tokenlist, expected_passwords, extra_cmd_line = b"", test_passwordlist = False,
                          chunksize = sys.maxint, expected_skipped = None, **extra_kwds):
        assert isinstance(tokenlist, list)
        assert isinstance(expected_passwords, list)
        tokenlist_str = "\n".join(tokenlist)
        args          = (b" __funccall --listpass "+extra_cmd_line).split()

        btcrecover.parse_arguments([b"--tokenlist"] + args, tokenlist=StringIO(tokenlist_str), **extra_kwds)
        tok_it, skipped = btcrecover.password_generator_factory(chunksize)
        if expected_skipped is not None:
            self.assertEqual(skipped, expected_skipped)
        try:
            self.assertEqual(tok_it.next(), expected_passwords)
        except StopIteration:
            self.assertEqual([], expected_passwords)
        if not test_passwordlist: return tok_it,

        # Reset any files passed in as extra parameters
        for sio in filter(lambda s: isinstance(s, NonClosingBase), extra_kwds.values()):
            sio.seek(0)

        btcrecover.parse_arguments([b"--passwordlist"] + args, passwordlist=StringIO(tokenlist_str), **extra_kwds)
        pwl_it, skipped = btcrecover.password_generator_factory(chunksize)
        if expected_skipped is not None:
            self.assertEqual(skipped, expected_skipped)
        try:
            self.assertEqual(pwl_it.next(), expected_passwords)
        except StopIteration:
            self.assertEqual([], expected_passwords)
        return tok_it, pwl_it

    # tokenlist == a list of lines (w/o "\n") which will become the tokenlist file
    # expected_error == a (partial) error message that should be produced from the tokenlist
    # extra_cmd_line == a single string of additional command-line options
    # extra_kwds == additional StringIO objects to act as file stand-ins
    def expect_syntax_failure(self, tokenlist, expected_error, extra_cmd_line = b"", **extra_kwds):
        assert isinstance(tokenlist, list)
        with self.assertRaises(SystemExit) as cm:
            btcrecover.parse_arguments(
                (b"--tokenlist __funccall --listpass "+extra_cmd_line).split(),
                tokenlist = StringIO("\n".join(tokenlist)),
                **extra_kwds)
        self.assertIn(expected_error, cm.exception.code)


class Test01Basics(GeneratorTester):

    def test_alternate(self):
        self.do_generator_test(["one", "two"], ["one", "two", "twoone", "onetwo"])
    @unittest.skipUnless(tstr == unicode, "Unicode builds only")
    def test_alternate_unicode(self):
        self.do_generator_test(["один", "два"], ["один", "два", "дваодин", "одиндва"])

    def test_mutex(self):
        self.do_generator_test(["one two three"], ["one", "two", "three"])

    def test_require(self):
        self.do_generator_test(["one", "+ two", "+ three"],
            ["threetwo", "twothree", "threetwoone", "threeonetwo",
            "twothreeone", "twoonethree", "onethreetwo", "onetwothree"])

    def test_chunksize_divisible(self):
        tok_it, = self.do_generator_test(["one two three four five six"], ["one", "two", "three"], b"", False, 3)
        self.assertEqual(tok_it.next(), ["four", "five", "six"])
        self.assertRaises(StopIteration, tok_it.next)
    def test_chunksize_indivisible(self):
        tok_it, = self.do_generator_test(["one two three four five"], ["one", "two", "three"], b"", False, 3)
        self.assertEqual(tok_it.next(), ["four", "five"])
        self.assertRaises(StopIteration, tok_it.next)
    def test_chunksize_modified(self):
        tok_it, = self.do_generator_test(["one two three four five six"], ["one", "two"], b"", False, 2)
        self.assertIsNone(tok_it.send( (3, False) ))
        self.assertEqual(tok_it.next(), ["three", "four", "five"])
        self.assertEqual(tok_it.next(), ["six"])
        self.assertRaises(StopIteration, tok_it.next)

    def test_only_yield_count(self):
        btcrecover.parse_arguments(b"--tokenlist __funccall --listpass".split(),
            tokenlist = StringIO("one two three four five six"))
        tok_it = btcrecover.password_generator(2, only_yield_count=True)
        self.assertEqual(tok_it.next(), 2)
        self.assertIsNone(tok_it.send( (3, True) ))
        self.assertEqual(tok_it.next(), 3)
        self.assertIsNone(tok_it.send( (3, False) ))
        self.assertEqual(tok_it.next(), ["six"])
        self.assertRaises(StopIteration, tok_it.next)

        btcrecover.parse_arguments(b"--passwordlist __funccall --listpass".split(),
            passwordlist = StringIO("one two three four five six".replace(" ", "\n")))
        pwl_it = btcrecover.password_generator(2, only_yield_count=True)
        self.assertEqual(pwl_it.next(), 2)
        self.assertIsNone(pwl_it.send( (3, True) ))
        self.assertEqual(pwl_it.next(), 3)
        self.assertIsNone(pwl_it.send( (3, False) ))
        self.assertEqual(pwl_it.next(), ["six"])
        self.assertRaises(StopIteration, pwl_it.next)

    def test_only_yield_count_all(self):
        btcrecover.parse_arguments(b"--tokenlist __funccall --listpass".split(),
            tokenlist = StringIO("one two three"))
        tok_it = btcrecover.password_generator(4, only_yield_count=True)
        self.assertEqual(tok_it.next(), 3)
        self.assertRaises(StopIteration, tok_it.next)

        btcrecover.parse_arguments(b"--passwordlist __funccall --listpass".split(),
            passwordlist = StringIO("one two three".replace(" ", "\n")))
        pwl_it = btcrecover.password_generator(4, only_yield_count=True)
        self.assertEqual(pwl_it.next(), 3)
        self.assertRaises(StopIteration, pwl_it.next)

    def test_count(self):
        btcrecover.parse_arguments(b"--tokenlist __funccall --listpass".split(),
            tokenlist = StringIO("one two three"))
        self.assertEqual(btcrecover.count_and_check_eta(1.0), 3)
    def test_count_zero(self):
        btcrecover.parse_arguments(b"--tokenlist __funccall --listpass".split(),
            tokenlist = StringIO(""))
        self.assertEqual(btcrecover.count_and_check_eta(1.0), 0)
    # the size of a "chunk" is == btcrecover.PASSWORDS_BETWEEN_UPDATES == 100000
    def test_count_one_chunk(self):
        assert btcrecover.PASSWORDS_BETWEEN_UPDATES == 100000
        btcrecover.parse_arguments(b"--tokenlist __funccall --listpass".split(),
            tokenlist = StringIO("%5d"))
        self.assertEqual(btcrecover.count_and_check_eta(1.0), 100000)
    def test_count_two_chunks(self):
        assert btcrecover.PASSWORDS_BETWEEN_UPDATES == 100000
        btcrecover.parse_arguments(b"--tokenlist __funccall --listpass".split(),
            tokenlist = StringIO("%5d 100000"))
        self.assertEqual(btcrecover.count_and_check_eta(1.0), 100001)

    def test_token_counts_min_0(self):
        self.do_generator_test(["one"], ["", "one"], b"--min-tokens 0")
    def test_token_counts_min_2(self):
        self.do_generator_test(["one", "two", "three"],
            ["twoone", "onetwo", "threeone", "onethree", "threetwo", "twothree", "threetwoone",
            "threeonetwo", "twothreeone", "twoonethree", "onethreetwo", "onetwothree"],
            b"--min-tokens 2")
    def test_token_counts_max_2(self):
        self.do_generator_test(["one", "two", "three"],
            ["one", "two", "twoone", "onetwo", "three", "threeone", "onethree", "threetwo", "twothree"],
            b"--max-tokens 2")
    def test_token_counts_min_max_2(self):
        self.do_generator_test(["one", "two", "three"],
            ["twoone", "onetwo", "threeone", "onethree", "threetwo", "twothree"],
            b"--min-tokens 2 --max-tokens 2")

    def test_empty_file(self):
        self.do_generator_test([], [], test_passwordlist=True)
    def test_one_char_file(self):
        self.do_generator_test(["a"], ["a"], test_passwordlist=True)
    def test_comments(self):
        self.do_generator_test(["#one", " #two", "#three"], ["#two"])

    def test_z_all(self):
        self.do_generator_test(["1", "2 3", "+ 4 5"], map(tstr, [
            4,41,14,42,24,421,412,241,214,142,124,43,34,431,413,341,314,143,134,
            5,51,15,52,25,521,512,251,215,152,125,53,35,531,513,351,315,153,135]))


class Test02Anchors(GeneratorTester):

    def test_begin(self):
        self.do_generator_test(["^one", "^two", "three"],
            ["one", "two", "three", "onethree", "twothree"])
    def test_begin_0len(self):
        self.do_generator_test(["^"], [""])

    def test_end(self):
        self.do_generator_test(["one$", "two$", "three"],
            ["one", "two", "three", "threeone", "threetwo"])
    def test_end_0len(self):
        self.do_generator_test(["$"], [""])

    def test_begin_and_end(self):
        self.expect_syntax_failure(["^one$"], "token on line 1 is anchored with both ^ at the beginning and $ at the end")

    def test_positional(self):
        self.do_generator_test(["one", "^2^two", "^3^three"], ["one", "onetwo", "onetwothree"])
    def test_positional_old(self):
        self.do_generator_test(["one", "^2$two", "^3$three"], ["one", "onetwo", "onetwothree"])
    def test_positional_0len(self):
        self.do_generator_test(["+ ^1^", "^2^two"], ["", "two"])

    def test_positional_invalid(self):
        self.expect_syntax_failure(["^0^zero"], "anchor position of token on line 1 must be 1 or greater")

    def test_middle(self):
        self.do_generator_test(["^one", "^2,2^two", "^,3^three", "^,^four", "five$"],
            ["one", "five", "onefive", "onetwofive", "onethreefive", "onetwothreefive", "onefourfive",
            "onetwofourfive", "onefourthreefive", "onethreefourfive", "onetwothreefourfive"])
    def test_middle_old(self):
        self.do_generator_test(["^one", "^2,2$two", "^,3$three", "^,$four", "five$"],
            ["one", "five", "onefive", "onetwofive", "onethreefive", "onetwothreefive", "onefourfive",
            "onetwofourfive", "onefourthreefive", "onethreefourfive", "onetwothreefourfive"])
    def test_middle_0len(self):
        self.do_generator_test(["one", "+ ^,^", "^3^three"], ["onethree"])

    def test_middle_invalid_begin(self):
        self.expect_syntax_failure(["^1,^one"],  "anchor range of token on line 1 must begin with 2 or greater")
    def test_middle_invalid_range(self):
        self.expect_syntax_failure(["^3,2^one"], "anchor range of token on line 1 is invalid")
    def test_not_middle(self):
        self.do_generator_test(["^2,3one"], ["2,3one"])

    # test for the bug fixed in v0.11.1
    def test_tokens_duplicate(self):
        self.do_generator_test(["one", "one", "^,$two"], ["one", "oneone", "onetwoone"], b"-d")


LEET_MAP_FILE = os.path.join(typos_dir, "leet-map.txt")
class Test03WildCards(GeneratorTester):

    def test_basics_1(self):
        self.do_generator_test(["%d"], map(tstr, xrange(10)), b"--has-wildcards", True)
    def test_basics_2(self):
        self.do_generator_test(["%dtest"], [tstr(i)+"test" for i in xrange(10)], b"--has-wildcards", True)
    def test_basics_3(self):
        self.do_generator_test(["te%dst"], ["te"+tstr(i)+"st" for i in xrange(10)], b"--has-wildcards", True)
    def test_basics_4(self):
        self.do_generator_test(["test%d"], ["test"+tstr(i) for i in xrange(10)], b"--has-wildcards", True)

    def test_invalid_nocust(self):
        self.expect_syntax_failure(["%c"],    "invalid wildcard")
    def test_invalid_nocust_cap(self):
        self.expect_syntax_failure(["%C"],    "invalid wildcard")
    def test_invalid_notype(self):
        self.expect_syntax_failure(["test%"], "invalid wildcard")

    def test_multiple(self):
        self.do_generator_test(["%d%d"], ["{:02}".format(i) for i in xrange(100)], b"--has-wildcards", True)

    def test_length_2(self):
        self.do_generator_test(["%2d"],  ["{:02}".format(i) for i in xrange(100)], b"--has-wildcards", True)
    def test_length_range(self):
        self.do_generator_test(["%0,2d"],
            [""] +
            map(tstr, xrange(10)) +
            ["{:02}".format(i) for i in xrange(100)],
            b"--has-wildcards", True)

    def test_length_invalid_range(self):
        self.expect_syntax_failure(["%2,1d"], "on line 1: max wildcard length (1) must be >= min length (2)")
    def test_invalid_length_1(self):
        self.expect_syntax_failure(["%2,d"],  "invalid wildcard")
    def test_invalid_length_2(self):
        self.expect_syntax_failure(["%,2d"],  "invalid wildcard")

    def test_case_lower(self):
        self.do_generator_test(["%a"], map(tchr, xrange(ord("a"), ord("z")+1)), b"--has-wildcards", True)
    def test_case_upper(self):
        self.do_generator_test(["%A"], map(tchr, xrange(ord("A"), ord("Z")+1)), b"--has-wildcards", True)
    def test_case_insensitive_1(self):
        self.do_generator_test(["%ia"],
            map(tchr, xrange(ord("a"), ord("z")+1)) + map(tchr, xrange(ord("A"), ord("Z")+1)), b"--has-wildcards", True)
    def test_case_insensitive_2(self):
        self.do_generator_test(["%iA"],
            map(tchr, xrange(ord("A"), ord("Z")+1)) + map(tchr, xrange(ord("a"), ord("z")+1)), b"--has-wildcards", True)

    def test_custom(self):
        self.do_generator_test(["%c"],  ["a", "b", "c", "D", "2"], b"--has-wildcards --custom-wild a-cD2", True)
    def test_custom_upper(self):
        self.do_generator_test(["%C"],  ["A", "B", "C", "D", "2"], b"--has-wildcards --custom-wild a-cD2", True)
    def test_custom_insensitive_1(self):
        self.do_generator_test(["%ic"], ["a", "b", "c", "D", "2", "A", "B", "C", "d"],
            b"--has-wildcards --custom-wild a-cD2 -d", True)
    def test_custom_insensitive_2(self):
        self.do_generator_test(["%iC"], ["A", "B", "C", "d", "2", "a", "b", "c", "D"],
            b"--has-wildcards --custom-wild a-cD2 -d", True)

    def test_set(self):
        self.do_generator_test(["%[abcc-]"], ["a", "b", "c", "-"], b"--has-wildcards -d", True)
    def test_set_insensitive(self):
        self.do_generator_test(["%i[abcc-]"], ["a", "b", "c", "-", "A", "B", "C"], b"--has-wildcards -d", True)
    def test_noset(self):
        self.do_generator_test(["%%[not-a-range]"], ["%[not-a-range]"], b"--has-wildcards", True)

    def test_range_1(self):
        self.do_generator_test(["%[1dc-f]"],  ["1", "d", "c", "e", "f"], b"--has-wildcards -d", True)
    def test_range_2(self):
        self.do_generator_test(["%[a-c-e]"], ["a", "b", "c", "-", "e"], b"--has-wildcards", True)
    def test_range_insensitive(self):
        self.do_generator_test(["%i[1dc-f]"], ["1", "d", "c", "e", "f", "D", "C", "E", "F"], b"--has-wildcards -d", True)

    def test_range_invalid(self):
        self.expect_syntax_failure(["%[c-a]"],  "first character in wildcard range 'c' > last 'a'")

    def test_contracting_1(self):
        self.do_generator_test(["a%0,2-bcd"], ["abcd", "bcd", "acd", "cd", "ad"], b"--has-wildcards -d", True)
    def test_contracting_2(self):
        self.do_generator_test(["abcd%1,2-"], ["abc", "ab"], b"--has-wildcards -d", True)
    def test_contracting_right(self):
        self.do_generator_test(["ab%0,1>cd"], ["abcd", "abd"], b"--has-wildcards -d", True)
    def test_contracting_left(self):
        self.do_generator_test(["ab%0,3<cd"], ["abcd", "acd", "cd"], b"--has-wildcards -d", True)
    def test_contracting_multiple(self):
        self.do_generator_test(["%0,3-ab%[X]cd%0,3-"],
            ["abXcd", "abXc", "abX", "bXcd", "bXc", "bX", "Xcd", "Xc", "X"], b"--has-wildcards -d", True)

    def test_backreference(self):
        self.do_generator_test(["%[ab]%b"], ["aa", "bb"], b"--has-wildcards -d", True)
    def test_backreference_length(self):
        self.do_generator_test(["%[ab]%2,3b"], ["aaa", "aaaa", "bbb", "bbbb"], b"--has-wildcards -d", True)
    def test_backreference_pos(self):
        self.do_generator_test(["%[ab]X%;2b"], ["aXa", "bXb"], b"--has-wildcards -d", True)
    def test_backreference_pos_length(self):
        self.do_generator_test(["%[ab]X%2,3;2b"], ["aXaX", "aXaXa", "bXbX", "bXbXb"], b"--has-wildcards -d", True)
    def test_backreference_bounds(self):
        self.do_generator_test(["%[ab]%1,3;3b"], ["a", "aa", "b", "bb"], b"--has-wildcards -d", True)

    @unittest.skipUnless(os.path.isfile(LEET_MAP_FILE), "requires leet-map.txt file")
    def test_backreference_map(self):
        self.do_generator_test(["%[bc]%;"+LEET_MAP_FILE+";b"],
            ["b8", "b6", "c("], b"--has-wildcards -d", True)
    @unittest.skipUnless(os.path.isfile(LEET_MAP_FILE), "requires leet-map.txt file")
    def test_backreference_map_missing(self):
        self.do_generator_test(["%[cd]%;"+LEET_MAP_FILE+";b"],
            ["c(", "dd"], b"--has-wildcards -d", True)
    @unittest.skipUnless(os.path.isfile(LEET_MAP_FILE), "requires leet-map.txt file")
    def test_backreference_map_length(self):
        self.do_generator_test(["%[bc]%2,3;"+LEET_MAP_FILE+";b"],
            ["b88", "b888", "b66", "b666", "c((", "c((("], b"--has-wildcards -d", True)
    @unittest.skipUnless(os.path.isfile(LEET_MAP_FILE), "requires leet-map.txt file")
    def test_backreference_map_pos(self):
        self.do_generator_test(["%[bc]X%;"+LEET_MAP_FILE+";2b"],
            ["bX8", "bX6", "cX("], b"--has-wildcards -d", True)
    @unittest.skipUnless(os.path.isfile(LEET_MAP_FILE), "requires leet-map.txt file")
    def test_backreference_map_pos_length(self):
        self.do_generator_test(["%[bc]X%2,3;"+LEET_MAP_FILE+";2b"],
            ["bX8%", "bX8%8", "bX6%", "bX6%6", "cX(%", "cX(%("], b"--has-wildcards -d", True)
    @unittest.skipUnless(os.path.isfile(LEET_MAP_FILE), "requires leet-map.txt file")
    def test_backreference_map_bounds(self):
        self.do_generator_test(["%[bc]%1,3;"+LEET_MAP_FILE+";3b"],
            ["b", "b8", "b6", "c", "c("], b"--has-wildcards -d", True)


class Test04Typos(GeneratorTester):

    def test_capslock(self):
        self.do_generator_test(["One2Three"], ["One2Three", "oNE2tHREE"],
            b"--typos-capslock --typos 2 -d", True)
    def test_capslock_nocaps(self):
        self.do_generator_test(["123"], ["123"],
            b"--typos-capslock --typos 2 -d", True)
    @unittest.skipUnless(tstr == unicode, "Unicode builds only")
    def test_capslock_unicode(self):
        self.do_generator_test(["Один2Три"], ["Один2Три", "оДИН2тРИ"],
            b"--typos-capslock --typos 2 -d", True)

    def test_swap(self):
        self.do_generator_test(["abcdd"], ["abcdd", "bacdd", "acbdd", "abdcd", "badcd"],
            b"--typos-swap --typos 2 -d", True)
    def test_swap_max(self):
        self.do_generator_test(["abcdd"], ["abcdd", "bacdd", "acbdd", "abdcd"],
            b"--typos-swap --max-typos-swap 1 --typos 2 -d", True)

    def test_repeat(self):
        self.do_generator_test(["abc"], ["abc", "aabc", "abbc", "abcc", "aabbc", "aabcc", "abbcc"],
            b"--typos-repeat --typos 2 -d", True)
    def test_repeat_max(self):
        self.do_generator_test(["abc"], ["abc", "aabc", "abbc", "abcc"],
            b"--typos-repeat --max-typos-repeat 1 --typos 2 -d", True)

    def test_delete(self):
        self.do_generator_test(["abc"], ["abc", "bc", "ac", "ab", "c", "b", "a"],
            b"--typos-delete --typos 2 -d", True)
    def test_delete_max(self):
        self.do_generator_test(["abc"], ["abc", "bc", "ac", "ab"],
            b"--typos-delete --max-typos-delete 1 --typos 2 -d", True)

    def test_case(self):
        self.do_generator_test(["abC1"], ["abC1", "AbC1", "aBC1", "abc1", "ABC1", "Abc1", "aBc1"],
            b"--typos-case --typos 2 -d", True)
    def test_case_max(self):
        self.do_generator_test(["abC1"], ["abC1", "AbC1", "aBC1", "abc1"],
            b"--typos-case --max-typos-case 1 --typos 2 -d", True)

    def test_closecase(self):
        self.do_generator_test(["one2Three"],
            ["one2Three", "One2Three", "one2three", "one2THree", "one2ThreE", "One2three",
            "One2THree", "One2ThreE", "one2tHree", "one2threE", "one2THreE"],
            b"--typos-closecase --typos 2 -d", True)
    def test_closecase_max(self):
        self.do_generator_test(["one2Three"],
            ["one2Three", "One2Three", "one2three", "one2THree", "one2ThreE"],
            b"--typos-closecase --max-typos-closecase 1 --typos 2 -d", True)

    def test_insert(self):
        self.do_generator_test(["abc"],
            ["abc", "Xabc", "aXbc", "abXc", "abcX", "XaXbc", "XabXc", "XabcX", "aXbXc", "aXbcX", "abXcX"],
            b"--typos-insert X --typos 2 -d", True)
    def test_insert_max(self):
        self.do_generator_test(["abc"],
            ["abc", "Xabc", "aXbc", "abXc", "abcX"],
            b"--typos-insert X --max-typos-insert 1 --typos 2 -d", True)
    def test_insert_adjacent_1(self):
        self.do_generator_test(["ab"], ["ab", "Xab", "aXb", "abX", "XXab", "XaXb", "XabX", "aXXb", "aXbX", "abXX"],
            b"--typos-insert X --typos 2 --max-adjacent-inserts 2 -d", True)
    def test_insert_adjacent_2(self):
        self.do_generator_test(["a"], ["a", "Xa", "aX", "XXa", "XaX", "aXX", "XXaX", "XaXX" ],
            b"--typos-insert X --typos 3 --max-adjacent-inserts 2 -d", True)
    def test_insert_wildcard(self):
        self.do_generator_test(["abc"], ["abc", "Xabc", "Yabc", "aXbc", "aYbc", "abXc", "abYc", "abcX", "abcY"],
            b"--typos-insert %[XY] -d", True)
    def test_insert_wildcard_adjacent(self):
        self.do_generator_test(["a"],
            ["a", "Xa", "Ya", "aX", "aY", "XXa", "XYa", "YXa", "YYa",
            b"XaX", "XaY", "YaX", "YaY", "aXX", "aXY", "aYX", "aYY"],
            b"--typos-insert %[XY] --typos 2 --max-adjacent-inserts 2 -d", True)
    def test_insert_invalid(self):
        self.expect_syntax_failure(["abc"], "contracting wildcards are not permitted here",
            b"--typos-insert %0,1-")

    def test_replace(self):
        self.do_generator_test(["abc"], ["abc", "Xbc", "aXc", "abX", "XXc", "XbX", "aXX"],
            b"--typos-replace X --typos 2 -d", True)
    def test_replace_max(self):
        self.do_generator_test(["abc"], ["abc", "Xbc", "aXc", "abX"],
            b"--typos-replace X --max-typos-replace 1 --typos 2 -d", True)
    def test_replace_wildcard(self):
        self.do_generator_test(["abc"], ["abc", "Xbc", "Ybc", "aXc", "aYc", "abX", "abY"],
            b"--typos-replace %[X-Y] -d", True)
    def test_replace_invalid(self):
        self.expect_syntax_failure(["abc"], "contracting wildcards are not permitted here",
            b"--typos-replace %>")

    def test_map(self):
        self.do_generator_test(["axb"],
            ["axb", "Axb", "Bxb", "axA", "axB", "AxA", "AxB", "BxA", "BxB"],
            b"--typos-map __funccall --typos 2 -d", True,
            typos_map=StringIONonClosing(" ab \t AB \n x x \n a aB "))
    def test_map_max(self):
        self.do_generator_test(["axb"],
            ["axb", "Axb", "Bxb", "axA", "axB"],
            b"--typos-map __funccall --max-typos-map 1 --typos 2 -d", True,
            typos_map=StringIONonClosing(" ab \t AB \n x x \n a aB "))

    def test_z_all(self):
        self.do_generator_test(["12"],
            map(tstr, [12,812,182,128,8812,8182,8128,1882,1828,1288,112,8112,1812,1182,
                1128,2,82,28,92,892,982,928,122,8122,1822,1282,1228,1,81,18,19,819,189,
                198,1122,11,119,22,"",9,922,9,99,21,821,281,218,221,1,91,211,2,29]),
            b"--typos-swap --typos-repeat --typos-delete --typos-case --typos-insert 8 --typos-replace 9 --typos 2 --max-adjacent-inserts 2 -d",
            True)

    def test_z_all_max(self):
        self.do_generator_test(["12"],
            map(tstr, [12,812,182,128,112,8112,1812,1182,1128,2,82,28,92,892,982,928,122,8122,1822,
                1282,1228,1,81,18,19,819,189,198,11,119,22,9,922,9,21,821,281,218,221,1,91,211,2,29]),
            b"--typos-swap --max-typos-swap 1 --typos-repeat --max-typos-repeat 1 --typos-delete --max-typos-delete 1 " + \
            b"--typos-case --typos-insert 8 --max-typos-insert 1 --typos-replace 9 --max-typos-replace 1 --typos 2 -d",
            True)

    def test_z_min_typos_1(self):
        self.do_generator_test(["12"],
            map(tstr, [88182,88128,81882,81828,81288,18828,18288,88112,81812,81182,81128,
                18812,18182,18128,11882,11828,11288,882,828,288,8892,8982,8928,9882,9828,
                9288,88122,81822,81282,81228,18822,18282,18228,12882,12828,12288,881,818,
                188,8819,8189,8198,1889,1898,1988,81122,18122,11822,11282,11228,811,181,
                118,8119,1819,1189,1198,822,282,228,8,89,98,8922,9822,9282,9228,89,98,899,
                989,998,8821,8281,8218,2881,2818,2188,8221,2821,2281,2218,81,18,891,981,
                918,8211,2811,2181,2118,82,28,829,289,298,2211,22,229,11,"",9,911,9,99]),
            b"--typos-swap --typos-repeat --typos-delete --typos-case --typos-insert 8 --typos-replace 9 --typos 3 --max-adjacent-inserts 2 --min-typos 3 -d",
            True)
    def test_z_min_typos_2(self):
        self.do_generator_test(["12"], [],
            b"--typos-swap --typos-repeat --typos-delete --typos-case --typos-replace 8 --typos 4 -d --min-typos 4",
            True)


LARGE_TOKENLIST_LEN = 2 * btcrecover.PASSWORDS_BETWEEN_UPDATES
LARGE_TOKENLIST     = " ".join(tstr(i) for i in xrange(LARGE_TOKENLIST_LEN))
LARGE_LAST_TOKEN    = tstr(LARGE_TOKENLIST_LEN - 1)
class Test05CommandLine(GeneratorTester):

    def test_embedded_tokenlist_option(self):
        self.do_generator_test(["#--typos-capslock", "one"], ["one", "ONE"])
    def test_embedded_tokenlist_overwridden_option(self):
        self.do_generator_test(["#--skip 1", "one two"], [], b"--skip 2")
    @unittest.skipUnless(tstr == unicode, "Unicode builds only")
    def test_embedded_tokenlist_option_unicode(self):
        self.do_generator_test(["#--typos-insert в", "да"], ["да", "вда", "два", "дав"])
    def test_embedded_tokenlist_option_invalid(self):
        self.expect_syntax_failure(["#--tokenlist file"], "--tokenlist option is not permitted inside a tokenlist file")

    def test_passwordlist_no_wildcards(self):
        btcrecover.parse_arguments(b"--passwordlist __funccall --listpass".split(),
            passwordlist = StringIO("%%"))
        tok_it, skipped = btcrecover.password_generator_factory(2)
        self.assertEqual(tok_it.next(), ["%%"])

    def test_regex_only(self):
        self.do_generator_test(["one", "two"], ["one", "twoone", "onetwo"], b"--regex-only o.e")

    def test_regex_never(self):
        self.do_generator_test(["one", "two"], ["two"], b"--regex-never o.e", True)

    def test_delimiter_tokenlist(self):
        self.do_generator_test([" one ** two **** "], [" one ", " two ", "", " "], b"--delimiter **")

    def test_delimiter_typosmap(self):
        self.do_generator_test(["axb"], ["axb", "Axb", " xb", "axA", "ax ", "AxA", "Ax ", " xA", " x " ],
            b"--delimiter ** --typos-map __funccall --typos 2 -d",
            True, typos_map=StringIONonClosing(" ab **A \n x **x"))

    # Try to test the myriad of --skip related boundary conditions in password_generator_factory()
    def test_skip(self):
        self.do_generator_test(["one", "two"], ["twoone", "onetwo"], b"--skip 2", False, sys.maxint, 2)
    def test_skip_all_exact(self):
        self.do_generator_test(["one"], [], b"--skip 1", True, sys.maxint, 1)
    def test_skip_all_pastend_1(self):
        self.do_generator_test(["one"], [], b"--skip 2", True, sys.maxint, 1)
    def test_skip_all_pastend_2(self):
        self.do_generator_test(["one"], [], b"--skip " + str(LARGE_TOKENLIST_LEN), True, sys.maxint, 1)
    def test_skip_empty_1(self):
        self.do_generator_test([], [], b"--skip 1", True, sys.maxint, 0)
    def test_skip_empty_2(self):
        self.do_generator_test([], [], b"--skip " + str(LARGE_TOKENLIST_LEN), True, sys.maxint, 0)
    def test_skip_large_1(self):
        self.do_generator_test([LARGE_TOKENLIST], [LARGE_LAST_TOKEN], b"-d --skip "+str(LARGE_TOKENLIST_LEN-1), False, sys.maxint, LARGE_TOKENLIST_LEN-1)
    def test_skip_large_1_all_exact(self):
        self.do_generator_test([LARGE_TOKENLIST], [],                 b"-d --skip "+str(LARGE_TOKENLIST_LEN  ), False, sys.maxint, LARGE_TOKENLIST_LEN)
    def test_skip_large_1_all_pastend(self):
        self.do_generator_test([LARGE_TOKENLIST], [],                 b"-d --skip "+str(LARGE_TOKENLIST_LEN+1), False, sys.maxint, LARGE_TOKENLIST_LEN)
    def test_skip_large_2(self):
        self.do_generator_test([LARGE_TOKENLIST + " last"], ["last"], b"-d --skip "+str(LARGE_TOKENLIST_LEN  ), False, sys.maxint, LARGE_TOKENLIST_LEN)
    def test_skip_large_2_all_exact(self):
        self.do_generator_test([LARGE_TOKENLIST + " last"], [],       b"-d --skip "+str(LARGE_TOKENLIST_LEN+1), False, sys.maxint, LARGE_TOKENLIST_LEN+1)
    def test_skip_large_2_all_pastend(self):
        self.do_generator_test([LARGE_TOKENLIST + " last"], [],       b"-d --skip "+str(LARGE_TOKENLIST_LEN+2), False, sys.maxint, LARGE_TOKENLIST_LEN+1)
    def test_skip_end2end(self):
        btcrecover.parse_arguments(b"--skip 2 --tokenlist __funccall --listpass".split(),
            tokenlist = StringIO("one \n two"))
        self.assertIn("2 password combinations (plus 2 skipped)", btcrecover.main()[1])
    def test_skip_end2end_all_exact(self):
        btcrecover.parse_arguments(b"--skip 4 --tokenlist __funccall --listpass".split(),
            tokenlist = StringIO("one \n two"))
        self.assertIn("0 password combinations (plus 4 skipped)", btcrecover.main()[1])
    def test_skip_end2end_all_pastend(self):
        btcrecover.parse_arguments(b"--skip 5 --tokenlist __funccall --listpass".split(),
            tokenlist = StringIO("one \n two"))
        self.assertIn("0 password combinations (plus 4 skipped)", btcrecover.main()[1])
    def test_skip_end2end_all_noeta(self):
        btcrecover.parse_arguments(b"--skip 5 --tokenlist __funccall --no-eta --data-extract".split(),
            tokenlist    = StringIO("one \n two"),
            data_extract = "bWI6oikebfNQTLk75CfI5X3svX6AC7NFeGsgTNXZfA==")  # dummy data-extract not actually tested
        self.assertIn("Skipped all 4 passwords", btcrecover.main()[1])

    def test_max_eta(self):
        btcrecover.parse_arguments(b"--max-eta 1 --tokenlist __funccall --data-extract".split(),
            tokenlist    = StringIO("1 2 3 4 5 6 7 8 9 10 11"),
            data_extract = "bWI6oikebfNQTLk75CfI5X3svX6AC7NFeGsgTNXZfA==")  # dummy data-extract not actually tested
        with self.assertRaises(SystemExit) as cm:
            btcrecover.count_and_check_eta(360.0)  # 360s * 11 passwords > 1 hour
        self.assertIn("at least 11 passwords to try, ETA > --max-eta option (1 hours)", cm.exception.code)
    def test_max_eta_ok(self):
        btcrecover.parse_arguments(b"--max-eta 1 --tokenlist __funccall --data-extract".split(),
            tokenlist    = StringIO("1 2 3 4 5 6 7 8 9 10"),
            data_extract = "bWI6oikebfNQTLk75CfI5X3svX6AC7NFeGsgTNXZfA==")  # dummy data-extract not actually tested
        self.assertEqual(btcrecover.count_and_check_eta(360.0), 10)  # 360s * 10 passwords <= 1 hour
    def test_max_eta_skip(self):
        btcrecover.parse_arguments(b"--max-eta 1 --skip 4 --tokenlist __funccall --data-extract".split(),
            tokenlist    = StringIO("1 2 3 4 5 6 7 8 9 10 11 12 13 14 15"),
            data_extract = "bWI6oikebfNQTLk75CfI5X3svX6AC7NFeGsgTNXZfA==")  # dummy data-extract not actually tested
        with self.assertRaises(SystemExit) as cm:
            btcrecover.count_and_check_eta(360.0)  # 360s * 11 passwords > 1 hour
        self.assertIn("at least 11 passwords to try, ETA > --max-eta option (1 hours)", cm.exception.code)
    def test_max_eta_skip_ok(self):
        btcrecover.parse_arguments(b"--max-eta 1 --skip 5 --tokenlist __funccall --data-extract".split(),
            tokenlist    = StringIO("1 2 3 4 5 6 7 8 9 10 11 12 13 14 15"),
            data_extract = "bWI6oikebfNQTLk75CfI5X3svX6AC7NFeGsgTNXZfA==")  # dummy data-extract not actually tested
        # 360s * 10 passwords <= 1 hour, but count_and_check_eta still returns the total count of 15
        self.assertEqual(btcrecover.count_and_check_eta(360.0), 15)

    def test_worker(self):
        self.do_generator_test(["one two three four five six seven eight"], ["one", "four", "seven"],
            b"--worker 1/3")
        self.do_generator_test(["one two three four five six seven eight"], ["two", "five", "eight"],
            b"--worker 2/3")
        self.do_generator_test(["one two three four five six seven eight"], ["three", "six"],
            b"--worker 3/3")

    def test_no_dupchecks_1(self):
        self.do_generator_test(["one", "one"], ["one", "one", "oneone", "oneone"], b"-ddd")
        self.do_generator_test(["one", "one"], ["one", "one", "oneone"], b"-dd")

    def test_no_dupchecks_2(self):
        self.do_generator_test(["one", "one"], ["one", "oneone"], b"-d")
        # Duplicate code works differently the second time around; test it also
        self.assertEqual(btcrecover.password_generator(3).next(), ["one", "oneone"])

    def test_no_dupchecks_3(self):
        self.do_generator_test(["%[ab] %[a-b]"], ["a", "b", "a", "b"], b"-d")
        self.do_generator_test(["%[ab] %[a-b]"], ["a", "b"])
        # Duplicate code works differently the second time around; test it also
        self.assertEqual(btcrecover.password_generator(3).next(), ["a", "b"])

    # Need to check four different code paths for --exclude-passwordlist
    def test_exclude(self):
        self.do_generator_test(["exc1 exc2 inc exc1 exc2"], ["inc"], b"--exclude-passwordlist __funccall",
                               exclude_passwordlist=StringIO("exc1\nexc2"))
    def test_exclude_nodupchecks(self):
        self.do_generator_test(["exc1 exc2 inc exc1 exc2"], ["inc"], b"--exclude-passwordlist __funccall -dd",
                               exclude_passwordlist=StringIO("exc1\nexc2"))
    def test_exclude_noeta(self):
        self.do_generator_test(["exc1 exc2 inc exc1 exc2"], ["inc"], b"--exclude-passwordlist __funccall --no-eta",
                               exclude_passwordlist=StringIO("exc1\nexc2"))
    def test_exclude_noeta_nodupchecks(self):
        self.do_generator_test(["exc1 exc2 inc exc1 exc2"], ["inc"], b"--exclude-passwordlist __funccall --no-eta -dd",
                               exclude_passwordlist=StringIO("exc1\nexc2"))


SAVESLOT_SIZE = 4096
AUTOSAVE_ARGS = b"--autosave __funccall --tokenlist __funccall --data-extract --no-progress --threads 1".split()
AUTOSAVE_TOKENLIST    = "^one \n two \n three \n"
AUTOSAVE_DATA_EXTRACT = "bWI6oikebfNQTLk75CfI5X3svX6AC7NFeGsgTNXZfA=="
class Test06AutosaveRestore(unittest.TestCase):

    autosave_file = BytesIONonClosing()

    def run_autosave_parse_arguments(self, autosave_file):
        btcrecover.parse_arguments(AUTOSAVE_ARGS,
            autosave     = autosave_file,
            tokenlist    = StringIO(AUTOSAVE_TOKENLIST),
            data_extract = AUTOSAVE_DATA_EXTRACT)

    def run_restore_parse_arguments(self, restore_file):
        btcrecover.parse_arguments(b"--restore __funccall".split(),
            restore      = restore_file,
            tokenlist    = StringIO(AUTOSAVE_TOKENLIST),
            data_extract = AUTOSAVE_DATA_EXTRACT)

    # These test_ functions are in alphabetical order (the same order they're executed in)

    # Create the initial autosave data
    def test_autosave(self):
        autosave_file = self.__class__.autosave_file
        self.run_autosave_parse_arguments(autosave_file)
        self.assertIn("Password search exhausted", btcrecover.main()[1])
        #
        # Load slot 0, and verify it was created before any passwords were tested
        autosave_file.seek(0)
        savestate = cPickle.load(autosave_file)
        self.assertEqual(savestate.get(b"skip"), 0)
        self.assertLessEqual(autosave_file.tell(), SAVESLOT_SIZE)
        #
        # Load slot 1, and verify it was created after all passwords were tested
        autosave_file.seek(SAVESLOT_SIZE)
        savestate = cPickle.load(autosave_file)
        self.assertEqual(savestate.get(b"skip"), 9)
        self.assertLessEqual(autosave_file.tell(), 2*SAVESLOT_SIZE)

    # Using --autosave, restore (a copy of) the autosave data created by test_autosave(),
    # and make sure all of the passwords have already been tested
    def test_autosave_restore(self):
        self.run_autosave_parse_arguments(BytesIONonClosing(self.__class__.autosave_file.getvalue()))
        self.assertIn("Skipped all 9 passwords, exiting", btcrecover.main()[1])

    # Using --restore, restore (a copy of) the autosave data created by test_autosave(),
    # and make sure all of the passwords have already been tested
    def test_restore(self):
        self.run_restore_parse_arguments(BytesIONonClosing(self.__class__.autosave_file.getvalue()))
        self.assertIn("Skipped all 9 passwords, exiting", btcrecover.main()[1])

    # Using --autosave, restore (a copy of) the autosave data created by test_autosave(),
    # but change the arguments to generate an error
    def test_restore_changed_args(self):
        with self.assertRaises(SystemExit) as cm:
            btcrecover.parse_arguments(AUTOSAVE_ARGS + [b"--typos-capslock"],
                autosave     = BytesIO(self.__class__.autosave_file.getvalue()),
                tokenlist    = StringIO(AUTOSAVE_TOKENLIST),
                data_extract = AUTOSAVE_DATA_EXTRACT)
        self.assertIn("can't restore previous session: the command line options have changed", cm.exception.code)

    # Using --autosave, restore (a copy of) the autosave data created by test_autosave(),
    # but change the tokenlist file to generate an error
    def test_restore_changed_tokenlist(self):
        with self.assertRaises(SystemExit) as cm:
            btcrecover.parse_arguments(AUTOSAVE_ARGS,
                autosave     = BytesIO(self.__class__.autosave_file.getvalue()),
                tokenlist    = StringIO(AUTOSAVE_TOKENLIST + "four"),
                data_extract = AUTOSAVE_DATA_EXTRACT)
        self.assertIn("can't restore previous session: the tokenlist file has changed", cm.exception.code)

    # Using --restore, restore (a copy of) the autosave data created by test_autosave(),
    # but change the data_extract to generate an error
    def test_restore_changed_data_extract(self):
        with self.assertRaises(SystemExit) as cm:
            btcrecover.parse_arguments(b"--restore __funccall".split(),
                restore      = BytesIO(self.__class__.autosave_file.getvalue()),
                tokenlist    = StringIO(AUTOSAVE_TOKENLIST),
                data_extract = "bWI6ACkebfNQTLk75CfI5X3svX6AC7NFeGsgUxKNFg==")  # has a valid CRC
        self.assertIn("can't restore previous session: the encrypted key entered is not the same", cm.exception.code)

    # Using --restore, restore the autosave data created by test_autosave(),
    # but remove the last byte from slot 1 to make it invalid
    def test_restore_truncated(self):
        autosave_file = self.__class__.autosave_file
        autosave_file.seek(-1, os.SEEK_END)
        autosave_file.truncate()
        self.run_restore_parse_arguments(autosave_file)
        #
        # Slot 1 had the final save, but since it is invalid, the loader should fall
        # back to slot 0 with the initial save, so the passwords should be tried again.
        self.assertIn("Password search exhausted", btcrecover.main()[1])
        #
        # Because slot 1 was invalid, it is the first slot overwritten. Load it, and
        # verify it was written to before any passwords were tested
        autosave_file.seek(SAVESLOT_SIZE)
        savestate = cPickle.load(autosave_file)
        self.assertEqual(savestate.get(b"skip"), 0)
        #
        # Load slot 0 (the second slot overwritten), and verify it was written to
        # after all passwords were tested
        autosave_file.seek(0)
        savestate = cPickle.load(autosave_file)
        self.assertEqual(savestate.get(b"skip"), 9)


is_armory_loadable = None
def can_load_armory(permit_unicode = False):
    if tstr == unicode and not permit_unicode:
        return False
    global is_armory_loadable
    # Don't call the load function more than once
    # (calling more than once on success is OK though)
    if is_armory_loadable is None:
        try:
            btcrecover.load_armory_library(permit_unicode)
            is_armory_loadable = True
        except ImportError:
            is_armory_loadable = False
    return is_armory_loadable

is_protobuf_loadable = None
def can_load_protobuf():
    global is_protobuf_loadable
    if is_protobuf_loadable is None:
        try:
            import wallet_pb2
            is_protobuf_loadable = True
        except ImportError:
            is_protobuf_loadable = False
    return is_protobuf_loadable

pylibscrypt = None
def can_load_scrypt():
    global pylibscrypt
    if pylibscrypt is None:
        try:
            import pylibscrypt
        except ImportError:
            pylibscrypt = False
    return pylibscrypt and pylibscrypt._done  # True iff a binary implementation was found


class Test07WalletDecryption(unittest.TestCase):

    # Checks a test wallet against the known password, and ensures
    # that the library doesn't make any changes to the wallet file
    def wallet_tester(self, wallet_basename, force_purepython = False, force_kdf_purepython = False,
                      correct_pass = None, blockchain_mainpass = None, android_backuppass = None):
        assert os.path.basename(wallet_basename) == wallet_basename
        wallet_filename = os.path.join(wallet_dir, wallet_basename)

        temp_dir = tempfile.mkdtemp("-test-btcr")
        temp_wallet_filename = os.path.join(temp_dir, wallet_basename)
        shutil.copyfile(wallet_filename, temp_wallet_filename)

        if android_backuppass:
            wallet = btcrecover.WalletAndroidSpendingPIN.load_from_filename(
                temp_wallet_filename, android_backuppass, force_purepython)
        elif blockchain_mainpass:
            wallet = btcrecover.WalletBlockchainSecondpass.load_from_filename(
                temp_wallet_filename, blockchain_mainpass, force_purepython)
        else:
            wallet = btcrecover.load_wallet(temp_wallet_filename)

        if force_purepython:     btcrecover.load_aes256_library(force_purepython=True)
        if force_kdf_purepython: btcrecover.load_pbkdf2_library(force_purepython=True)

        if not correct_pass:
            correct_pass = "btcr-test-password"
        self.assertEqual(wallet.return_verified_password_or_false(
            ["btcr-wrong-password-1", "btcr-wrong-password-2"]), (False, 2))
        self.assertEqual(wallet.return_verified_password_or_false(
            ["btcr-wrong-password-3", correct_pass, "btcr-wrong-password-4"]), (correct_pass, 2))

        del wallet
        self.assertTrue(filecmp.cmp(wallet_filename, temp_wallet_filename, False))  # False == always compare file contents
        shutil.rmtree(temp_dir)

    @unittest.skipUnless(can_load_armory(), "requires Armory and ASCII version of btcrecover")
    def test_armory(self):
        self.wallet_tester("armory-wallet.wallet")

    @unittest.skipUnless(btcrecover.load_aes256_library().__name__ == b"Crypto", "requires PyCrypto")
    def test_bitcoincore(self):
        self.wallet_tester("bitcoincore-wallet.dat")

    @unittest.skipUnless(btcrecover.load_aes256_library().__name__ == b"Crypto", "requires PyCrypto")
    def test_electrum(self):
        self.wallet_tester("electrum-wallet")

    @unittest.skipUnless(btcrecover.load_aes256_library().__name__ == b"Crypto", "requires PyCrypto")
    def test_electrum2(self):
        self.wallet_tester("electrum2-wallet")

    def test_electrum2_upgradedfrom_electrum1(self):
        self.wallet_tester("electrum1-upgradedto-electrum2-wallet")

    @unittest.skipUnless(btcrecover.load_aes256_library().__name__ == b"Crypto", "requires PyCrypto")
    def test_multibit(self):
        self.wallet_tester("multibit-wallet.key")

    @unittest.skipUnless(btcrecover.load_aes256_library().__name__ == b"Crypto", "requires PyCrypto")
    @unittest.skipUnless(can_load_scrypt(), "requires a binary implementation of pylibscrypt")
    def test_multibithd(self):
        self.wallet_tester("mbhd.wallet.aes")

    @unittest.skipUnless(btcrecover.load_aes256_library().__name__ == b"Crypto", "requires PyCrypto")
    @unittest.skipUnless(can_load_protobuf(), "requires protobuf")
    @unittest.skipUnless(can_load_scrypt(),   "requires a binary implementation of pylibscrypt")
    def test_bitcoinj(self):
        self.wallet_tester("bitcoinj-wallet.wallet")

    @unittest.skipUnless(btcrecover.load_aes256_library().__name__ == b"Crypto", "requires PyCrypto")
    @unittest.skipUnless(can_load_protobuf(), "requires protobuf")
    @unittest.skipUnless(can_load_scrypt(),   "requires a binary implementation of pylibscrypt")
    def test_androidpin(self):
        self.wallet_tester("android-bitcoin-wallet-backup",
                           android_backuppass="btcr-test-password", correct_pass="123456")

    @unittest.skipUnless(can_load_protobuf(), "requires protobuf")
    @unittest.skipUnless(can_load_scrypt(),   "requires a binary implementation of pylibscrypt")
    def test_androidpin_unencrypted(self):
        self.wallet_tester("bitcoinj-wallet.wallet", android_backuppass="IGNORED")

    @unittest.skipUnless(btcrecover.load_aes256_library().__name__ == b"Crypto", "requires PyCrypto")
    @unittest.skipUnless(can_load_scrypt(), "requires a binary implementation of pylibscrypt")
    def test_bither(self):
        self.wallet_tester("bither-wallet.db")

    @unittest.skipUnless(btcrecover.load_aes256_library().__name__ == b"Crypto", "requires PyCrypto")
    def test_msigna(self):
        self.wallet_tester("msigna-wallet.vault")

    @unittest.skipUnless(btcrecover.load_aes256_library().__name__ == b"Crypto" and
                         btcrecover.load_pbkdf2_library().__name__ == b"hashlib",
                         "requires PyCrypto and Python 2.7.8+")
    def test_blockchain_v0(self):
        self.wallet_tester("blockchain-v0.0-wallet.aes.json")

    @unittest.skipUnless(btcrecover.load_aes256_library().__name__ == b"Crypto" and
                         btcrecover.load_pbkdf2_library().__name__ == b"hashlib",
                         "requires PyCrypto and Python 2.7.8+")
    def test_blockchain_v2(self):
        self.wallet_tester("blockchain-v2.0-wallet.aes.json")

    @unittest.skipUnless(btcrecover.load_aes256_library().__name__ == b"Crypto" and
                         btcrecover.load_pbkdf2_library().__name__ == b"hashlib",
                         "requires PyCrypto and Python 2.7.8+")
    def test_blockchain_secondpass_v0(self):
        self.wallet_tester("blockchain-v0.0-wallet.aes.json", blockchain_mainpass="btcr-test-password")

    @unittest.skipUnless(btcrecover.load_aes256_library().__name__ == b"Crypto" and
                         btcrecover.load_pbkdf2_library().__name__ == b"hashlib",
                         "requires PyCrypto and Python 2.7.8+")
    def test_blockchain_secondpass_v2(self):
        self.wallet_tester("blockchain-v2.0-wallet.aes.json", blockchain_mainpass="btcr-test-password")

    @unittest.skipUnless(btcrecover.load_pbkdf2_library().__name__ == b"hashlib", "requires Python 2.7.8+")
    def test_blockchain_secondpass_unencrypted(self):  # this wallet has no second-password iter_count, so this case is also tested here
        self.wallet_tester("blockchain-unencrypted-wallet.aes.json", blockchain_mainpass="IGNORED")

    def test_bitcoincore_pywallet(self):
        self.wallet_tester("bitcoincore-pywallet-dumpwallet.txt")

    # Make sure the Blockchain wallet loader can heuristically determine that files containing
    # base64 data that doesn't look entirely encrypted (random) are not Blockchain wallets
    def test_blockchain_invalid(self):
        # A base64-containing file that's mostly but not entirely encrypted (random)
        with self.assertRaises(ValueError) as cm:
            btcrecover.WalletBlockchain.load_from_filename(os.path.join(wallet_dir, "multibit-wallet.key"))
        self.assertIn("Doesn't look random enough to be an encrypted Blockchain wallet", cm.exception.args[0])

    def test_bitcoincore_pp(self):
        self.wallet_tester("bitcoincore-wallet.dat", force_purepython=True)

    def test_electrum_pp(self):
        self.wallet_tester("electrum-wallet", force_purepython=True)

    def test_electrum2_pp(self):
        self.wallet_tester("electrum2-wallet", force_purepython=True)

    def test_multibit_pp(self):
        self.wallet_tester("multibit-wallet.key", force_purepython=True)

    @unittest.skipUnless(can_load_scrypt(), "requires a binary implementation of pylibscrypt")
    def test_multibithd_pp(self):
        self.wallet_tester("mbhd.wallet.aes", force_purepython=True)

    @unittest.skipUnless(can_load_protobuf(), "requires protobuf")
    @unittest.skipUnless(can_load_scrypt(),   "requires a binary implementation of pylibscrypt")
    def test_bitcoinj_pp(self):
        self.wallet_tester("bitcoinj-wallet.wallet", force_purepython=True)

    @unittest.skipUnless(can_load_protobuf(), "requires protobuf")
    @unittest.skipUnless(can_load_scrypt(),   "requires a binary implementation of pylibscrypt")
    def test_androidpin_pp(self):
        self.wallet_tester("android-bitcoin-wallet-backup", force_purepython=True,
                           android_backuppass="btcr-test-password", correct_pass="123456")

    @unittest.skipUnless(can_load_scrypt(), "requires a binary implementation of pylibscrypt")
    def test_bither_pp(self):
        self.wallet_tester("bither-wallet.db", force_purepython=True)

    def test_msigna_pp(self):
        self.wallet_tester("msigna-wallet.vault", force_purepython=True)

    def test_blockchain_v0_pp(self):
        self.wallet_tester("blockchain-v0.0-wallet.aes.json", force_purepython=True, force_kdf_purepython=True)

    def test_blockchain_v2_pp(self):
        self.wallet_tester("blockchain-v2.0-wallet.aes.json", force_purepython=True, force_kdf_purepython=True)

    def test_blockchain_secondpass_v0_pp(self):
        self.wallet_tester("blockchain-v0.0-wallet.aes.json", force_purepython=True, force_kdf_purepython=True,
                           blockchain_mainpass="btcr-test-password")

    def test_blockchain_secondpass_v2_pp(self):
        self.wallet_tester("blockchain-v2.0-wallet.aes.json", force_purepython=True, force_kdf_purepython=True,
                           blockchain_mainpass="btcr-test-password")

    def test_blockchain_secondpass_unencrypted_pp(self):  # this wallet has no second-password iter_count, so this case is also tested here
        self.wallet_tester("blockchain-unencrypted-wallet.aes.json", force_kdf_purepython=True, blockchain_mainpass="IGNORED")

    def test_invalid_wallet(self):
        with self.assertRaises(SystemExit) as cm:
            btcrecover.load_wallet(__file__)
        self.assertIn("unrecognized wallet format", cm.exception.code)


class Test08BIP39Passwords(unittest.TestCase):

    def bip39_tester(self, force_purepython = False, unicode_pw = False, *args, **kwargs):

        btcrecover.loaded_wallet = btcrecover.WalletBIP39(*args, **kwargs)
        if force_purepython: btcrecover.load_pbkdf2_library(force_purepython=True)

        correct_pw = "btcr-test-password" if not unicode_pw else "btcr-тест-пароль"
        self.assertEqual(btcrecover.return_verified_password_or_false(
            ["btcr-wrong-password-1", "btcr-wrong-password-2"]), (False, 2))
        self.assertEqual(btcrecover.return_verified_password_or_false(
            ["btcr-wrong-password-3", correct_pw, "btcr-wrong-password-4"]), (correct_pw, 2))

    @unittest.skipUnless(can_load_armory(permit_unicode=True), "requires Armory")
    @unittest.skipUnless(btcrecover.load_pbkdf2_library().__name__ == b"hashlib",
                         "requires Python 2.7.8+")
    def test_bip39_mpk(self):
        self.bip39_tester(
            mpk=      "xpub6D3uXJmdUg4xVnCUkNXJPCkk18gZAB8exGdQeb2rDwC5UJtraHHARSCc2Nz7rQ14godicjXiKxhUn39gbAw6Xb5eWb5srcbkhqPgAqoTMEY",
            mnemonic= "certain come keen collect slab gauge photo inside mechanic deny leader drop"
        )

    @unittest.skipUnless(can_load_armory(permit_unicode=True), "requires Armory")
    @unittest.skipUnless(tstr == unicode, "Unicode builds only")
    def test_bip39_unicode_password(self):
        self.bip39_tester(
            mpk=        "xpub6CZe1G1A1CaaSepbekLMSk1sBRNA9kHZzEQCedudHAQHHB21FW9fYpQWXBevrLVQfL8JFQVFWEw3aACdr6szksaGsLiHDKyRd1rPJ6ev5ig",
            mnemonic=   "certain come keen collect slab gauge photo inside mechanic deny leader drop",
            unicode_pw= True
        )

    @unittest.skipUnless(can_load_armory(permit_unicode=True), "requires Armory")
    def test_bip39_unicode_mnemonic(self):
        self.bip39_tester(
            mpk=       "xpub6C7cXo5w4HPs6X93zKdkRNDFyHedGHwQHvmMst7HYjeudySyF3eTsWktz6JVz4CkrzuLiEbieYP8dQaxsffJXjquD3FLmnqioHe8qZwcBF3",
            mnemonic= u"あんまり　おんがく　いとこ　ひくい　こくはく　あらゆる　てあし　げどく　はしる　げどく　そぼろ　はみがき"
        )

    @unittest.skipUnless(can_load_armory(permit_unicode=True), "requires Armory")
    def test_bip39_address(self):
        self.bip39_tester(
            address=       "1AmugMgC6pBbJGYuYmuRrEpQVB9BBMvCCn",
            address_limit= 5,
            mnemonic=      "certain come keen collect slab gauge photo inside mechanic deny leader drop"
        )

    @unittest.skipUnless(can_load_armory(permit_unicode=True), "requires Armory")
    def test_bip39_pp(self):
        self.bip39_tester(
            mpk=              "xpub6D3uXJmdUg4xVnCUkNXJPCkk18gZAB8exGdQeb2rDwC5UJtraHHARSCc2Nz7rQ14godicjXiKxhUn39gbAw6Xb5eWb5srcbkhqPgAqoTMEY",
            mnemonic=         "certain come keen collect slab gauge photo inside mechanic deny leader drop",
            force_purepython= True
        )


def has_any_opencl_devices():
    try:   devs = btcrecover.get_opencl_devices()
    except ImportError: return False
    return len(devs) > 0


class Test08KeyDecryption(unittest.TestCase):

    def key_tester(self, key_crc_base64, force_purepython = False, force_kdf_purepython = False, unicode_pw = False):
        btcrecover.load_from_base64_key(key_crc_base64)
        if force_purepython:     btcrecover.load_aes256_library(force_purepython=True)
        if force_kdf_purepython: btcrecover.load_pbkdf2_library(force_purepython=True)

        correct_pw = "btcr-test-password" if not unicode_pw else "btcr-тест-пароль"
        self.assertEqual(btcrecover.return_verified_password_or_false(
            ["btcr-wrong-password-1", "btcr-wrong-password-2"]), (False, 2))
        self.assertEqual(btcrecover.return_verified_password_or_false(
            ["btcr-wrong-password-3", correct_pw, "btcr-wrong-password-4"]), (correct_pw, 2))

    @unittest.skipUnless(can_load_armory(), "requires Armory and ASCII version of btcrecover")
    def test_armory(self):
        self.key_tester("YXI6r7mks1qvph4G+rRT7WlIptdr9qDqyFTfXNJ3ciuWJ12BgWX5Il+y28hLNr/u4Wl49hUi4JBeq6Jz9dVBX3vAJ6476FEAACAABAAAAGGwnwXRpPbBzC5lCOBVVWDu7mUJetBOBvzVAv0IbrboDXqA8A==")

    @unittest.skipUnless(btcrecover.load_aes256_library().__name__ == b"Crypto", "requires PyCrypto")
    def test_bitcoincore(self):
        self.key_tester("YmM65iRhIMReOQ2qaldHbn++T1fYP3nXX5tMHbaA/lqEbLhFk6/1Y5F5x0QJAQBI/maR")
    #
    @unittest.skipUnless(tstr == unicode, "Unicode builds only")
    @unittest.skipUnless(btcrecover.load_aes256_library().__name__ == b"Crypto", "requires PyCrypto")
    def test_bitcoincore_unicode(self):
        self.key_tester("YmM6XAL2X19VfzlKJfc+7LIeNrB2KC8E9DWe1YhhOchPoClvwftbuqjXKkfdAAARmggo", unicode_pw=True)

    @unittest.skipUnless(btcrecover.load_aes256_library().__name__ == b"Crypto", "requires PyCrypto")
    def test_multibit(self):
        self.key_tester("bWI6oikebfNQTLk75CfI5X3svX6AC7NFeGsgTNXZfA==")
    #
    @unittest.skipUnless(tstr == unicode, "Unicode builds only")
    @unittest.skipUnless(btcrecover.load_aes256_library().__name__ == b"Crypto", "requires PyCrypto")
    def test_multibit_unicode(self):
        self.key_tester("bWI6YK6OX8bVP2Ar/j2dZBBQ+F0pEn8kZK6rlXiAWA==", unicode_pw=True)

    @unittest.skipUnless(btcrecover.load_aes256_library().__name__ == b"Crypto", "requires PyCrypto")
    def test_multidoge(self):
        self.key_tester("bWI6IdK25nMhHI9n4zlb1cUtWBl7mL7gh7ZtxkYaDw==")
    #
    @unittest.skipUnless(tstr == unicode, "Unicode builds only")
    @unittest.skipUnless(btcrecover.load_aes256_library().__name__ == b"Crypto", "requires PyCrypto")
    def test_multidoge_unicode(self):
        self.key_tester("bWI6ry78W+RkeTi2dVt2omZMfXRi46xDsIhr0jKN3g==", unicode_pw=True)

    @unittest.skipUnless(btcrecover.load_aes256_library().__name__ == b"Crypto", "requires PyCrypto")
    def test_androidwallet(self):
        self.key_tester("bWI6Ii/ZEeDjUJKq704wzUxKudpvAralnrOQtXM4og==")
    #
    @unittest.skipUnless(tstr == unicode, "Unicode builds only")
    @unittest.skipUnless(btcrecover.load_aes256_library().__name__ == b"Crypto", "requires PyCrypto")
    def test_androidwallet_unicode(self):
        self.key_tester("bWI6f1QdX7xXtC0zG7XK9pTGTifie5FUeAGhJ05esw==", unicode_pw=True)

    @unittest.skipUnless(btcrecover.load_aes256_library().__name__ == b"Crypto", "requires PyCrypto")
    def test_androidknc(self):
        self.key_tester("bWI6n6ccPSkbrmxQpdfKNAOBFppQLGloPDHE2sOucQ====")
    #
    @unittest.skipUnless(tstr == unicode, "Unicode builds only")
    @unittest.skipUnless(btcrecover.load_aes256_library().__name__ == b"Crypto", "requires PyCrypto")
    def test_androidknc_unicode(self):
        self.key_tester("bWI6TaEiZOBE+52jqe09jKcVa39KqvOpJxbpEtCVPQ==", unicode_pw=True)

    @unittest.skipUnless(btcrecover.load_aes256_library().__name__ == b"Crypto", "requires PyCrypto")
    @unittest.skipUnless(can_load_scrypt(), "requires a binary implementation of pylibscrypt")
    def test_multibithd(self):
        self.key_tester("bTI6LbH/+ROEa0cQ0inH7V3thbdFJV4=")
    #
    @unittest.skipUnless(tstr == unicode, "Unicode builds only")
    @unittest.skipUnless(btcrecover.load_aes256_library().__name__ == b"Crypto", "requires PyCrypto")
    @unittest.skipUnless(can_load_scrypt(), "requires a binary implementation of pylibscrypt")
    def test_multibithd_unicode(self):
        self.key_tester("bTI6M7wXqwXQWo4o22eN50PNnlkc/Qs=", unicode_pw=True)

    @unittest.skipUnless(can_load_protobuf(), "requires protobuf")
    @unittest.skipUnless(can_load_scrypt(),   "requires a binary implementation of pylibscrypt")
    @unittest.skipUnless(btcrecover.load_aes256_library().__name__ == b"Crypto", "requires PyCrypto")
    def test_bitcoinj(self):
        self.key_tester("Ymo6MacXiCd1+6/qtPc5rCaj6qIGJbu5tX2PXQXqF4Df/kFrjNGMDMHqrwBAAAAIAAEAZwdBow==")
    #
    @unittest.skipUnless(tstr == unicode, "Unicode builds only")
    @unittest.skipUnless(can_load_protobuf(), "requires protobuf")
    @unittest.skipUnless(can_load_scrypt(),   "requires a binary implementation of pylibscrypt")
    @unittest.skipUnless(btcrecover.load_aes256_library().__name__ == b"Crypto", "requires PyCrypto")
    def test_bitcoinj_unicode(self):
        self.key_tester("Ymo6hgWTejxVYfL/LLF4af8j2RfEsi5y16kTQhECWnn9iCt8AmGWPoPomQBAAAAIAAEAfNRA3A==", unicode_pw=True)

    @unittest.skipUnless(can_load_scrypt(), "requires a binary implementation of pylibscrypt")
    @unittest.skipUnless(btcrecover.load_aes256_library().__name__ == b"Crypto", "requires PyCrypto")
    def test_bither(self):
        self.key_tester("YnQ6PocfHvWGVbCzlVb9cUtPDjosnuB7RoyspTEzZZAqURlCsLudQaQ4IkIW8YE=")
    #
    @unittest.skipUnless(tstr == unicode, "Unicode builds only")
    @unittest.skipUnless(can_load_scrypt(), "requires a binary implementation of pylibscrypt")
    @unittest.skipUnless(btcrecover.load_aes256_library().__name__ == b"Crypto", "requires PyCrypto")
    def test_bither_unicode(self):
        self.key_tester("YnQ6ENNU1KSJlzC8FMfAq/MHgWgaZkxpiByt/vLQ/UdP2NlCsLudQaQ4IjTbPcw=", unicode_pw=True)

    @unittest.skipUnless(btcrecover.load_aes256_library().__name__ == b"Crypto", "requires PyCrypto")
    def test_msigna(self):
        self.key_tester("bXM6SWd6U+qTKOzQDfz8auBL1/tzu0kap7NMOqctt7U0nA8XOI6j6BCjxCsc7mU=")
    #
    @unittest.skipUnless(tstr == unicode, "Unicode builds only")
    @unittest.skipUnless(btcrecover.load_aes256_library().__name__ == b"Crypto", "requires PyCrypto")
    def test_msigna_unicode(self):
        self.key_tester("bXM6i9OkMzrIJqWvpM+Dxq795jeFFxiB6DtBwuGmeEtfHLLOjMvoJRAWeSsf+Pg=", unicode_pw=True)

    @unittest.skipUnless(btcrecover.load_aes256_library().__name__ == b"Crypto", "requires PyCrypto")
    def test_electrum(self):
        self.key_tester("ZWw6kLJxTDF7LxneT7c5DblJ9k9WYwV6YUIUQO+IDiIXzMUZvsCT")
    #
    @unittest.skipUnless(tstr == unicode, "Unicode builds only")
    @unittest.skipUnless(btcrecover.load_aes256_library().__name__ == b"Crypto", "requires PyCrypto")
    def test_electrum_unicode(self):
        self.key_tester("ZWw6rLwP/stP422FgteriIgvq4LD90adedrAqz61gKuYDRrx3+Q+", unicode_pw=True)

    @unittest.skipUnless(btcrecover.load_aes256_library().__name__ == b"Crypto", "requires PyCrypto")
    def test_electrum2(self):
        self.key_tester("ZTI69B961mYKYFV7Bg1zRYZ8ZGw4cE+2D8NF3lp6d2XPe8qTdJUz")
    #
    @unittest.skipUnless(tstr == unicode, "Unicode builds only")
    @unittest.skipUnless(btcrecover.load_aes256_library().__name__ == b"Crypto", "requires PyCrypto")
    def test_electrum2_unicode(self):
        self.key_tester("ZTI6k2tz83Lzs83hyQPRj2g90f7nVYHYM20qLv4NIVIzUNNqVWv8", unicode_pw=True)

    @unittest.skipUnless(btcrecover.load_aes256_library().__name__ == b"Crypto" and
                         btcrecover.load_pbkdf2_library().__name__ == b"hashlib",
                         "requires PyCrypto and Python 2.7.8+")
    def test_blockchain_v0(self):
        self.key_tester("Yms69Z9y1J66ceYKkrXy11mHR+YDD8WrPJeTNaAnO7LO7YgAAAAAbnp7YQ==")
    #
    @unittest.skipUnless(tstr == unicode, "Unicode builds only")
    @unittest.skipUnless(btcrecover.load_aes256_library().__name__ == b"Crypto" and
                         btcrecover.load_pbkdf2_library().__name__ == b"hashlib",
                         "requires PyCrypto and Python 2.7.8+")
    def test_blockchain_v0_unicode(self):
        self.key_tester("Yms68OsennSoypcGGUvhrhEBFCiIkAK2Qphnfdc3Ungk/SoAAAAAcr6jYQ==", unicode_pw=True)

    @unittest.skipUnless(btcrecover.load_aes256_library().__name__ == b"Crypto" and
                         btcrecover.load_pbkdf2_library().__name__ == b"hashlib",
                         "requires PyCrypto and Python 2.7.8+")
    def test_blockchain_v2(self):
        self.key_tester("Yms6abF6aZYdu5sKpStKA4ihra6GEAeZTumFiIM0YQUkTjcQJwAAj8ekAQ==")

    @unittest.skipUnless(btcrecover.load_pbkdf2_library().__name__ == b"hashlib", "requires Python 2.7.8+")
    def test_blockchain_secondpass(self):                # extracted from blockchain-v0.0-wallet.aes.json which has a second password iter_count
        self.key_tester("YnM6ujsYxz3SE7fEEekfMuIC1oII7KY//j5FMObBn7HydqVyjnaeTCZDAaC4LbJcVkxaCgAAACsWXkw=")
    #
    @unittest.skipUnless(tstr == unicode, "Unicode builds only")
    @unittest.skipUnless(btcrecover.load_pbkdf2_library().__name__ == b"hashlib", "requires Python 2.7.8+")
    def test_blockchain_secondpass_unicode(self):
        self.key_tester("YnM6/e8Inpbesj+CYE0YvdXLewgN5UH9KFvliZrI43OmYnyHbCa71RBD57XO0CbuADDTCgAAACCVL/w=", unicode_pw=True)

    @unittest.skipUnless(btcrecover.load_pbkdf2_library().__name__ == b"hashlib", "requires Python 2.7.8+")
    def test_blockchain_secondpass_no_iter_count(self):  # extracted from blockchain-unencrypted-wallet.aes.json which is missing a second password iter_count
        self.key_tester("YnM6ujsYxz3SE7fEEekfMuIC1oII7KY//j5FMObBn7HydqVyjnaeTCZDAaC4LbJcVkxaAAAAAE/24yM=")

    def test_bitcoincore_pp(self):
        self.key_tester("YmM65iRhIMReOQ2qaldHbn++T1fYP3nXX5tMHbaA/lqEbLhFk6/1Y5F5x0QJAQBI/maR", force_purepython=True)
    #
    @unittest.skipUnless(tstr == unicode, "Unicode builds only")
    def test_bitcoincore_unicode_pp(self):
        self.key_tester("YmM6XAL2X19VfzlKJfc+7LIeNrB2KC8E9DWe1YhhOchPoClvwftbuqjXKkfdAAARmggo", force_purepython=True, unicode_pw=True)

    def test_multibit_pp(self):
        self.key_tester("bWI6oikebfNQTLk75CfI5X3svX6AC7NFeGsgTNXZfA==", force_purepython=True)
    #
    @unittest.skipUnless(tstr == unicode, "Unicode builds only")
    def test_multibit_unicode_pp(self):
        self.key_tester("bWI6YK6OX8bVP2Ar/j2dZBBQ+F0pEn8kZK6rlXiAWA==", force_purepython=True, unicode_pw=True)

    def test_multidoge_pp(self):
        self.key_tester("bWI6IdK25nMhHI9n4zlb1cUtWBl7mL7gh7ZtxkYaDw==", force_purepython=True)
    #
    @unittest.skipUnless(tstr == unicode, "Unicode builds only")
    def test_multidoge_unicode_pp(self):
        self.key_tester("bWI6ry78W+RkeTi2dVt2omZMfXRi46xDsIhr0jKN3g==", force_purepython=True, unicode_pw=True)

    def test_androidwallet_pp(self):
        self.key_tester("bWI6Ii/ZEeDjUJKq704wzUxKudpvAralnrOQtXM4og==", force_purepython=True)
    #
    @unittest.skipUnless(tstr == unicode, "Unicode builds only")
    def test_androidwallet_unicode_pp(self):
        self.key_tester("bWI6f1QdX7xXtC0zG7XK9pTGTifie5FUeAGhJ05esw==", force_purepython=True, unicode_pw=True)

    def test_androidknc_pp(self):
        self.key_tester("bWI6n6ccPSkbrmxQpdfKNAOBFppQLGloPDHE2sOucQ==", force_purepython=True)
    #
    @unittest.skipUnless(tstr == unicode, "Unicode builds only")
    def test_androidknc_unicode_pp(self):
        self.key_tester("bWI6TaEiZOBE+52jqe09jKcVa39KqvOpJxbpEtCVPQ==", force_purepython=True, unicode_pw=True)

    @unittest.skipUnless(can_load_scrypt(), "requires a binary implementation of pylibscrypt")
    def test_multibithd_pp(self):
        self.key_tester("bTI6LbH/+ROEa0cQ0inH7V3thbdFJV4=", force_purepython=True)
    #
    @unittest.skipUnless(tstr == unicode,   "Unicode builds only")
    @unittest.skipUnless(can_load_scrypt(), "requires a binary implementation of pylibscrypt")
    def test_multibithd_unicode_pp(self):
        self.key_tester("bTI6M7wXqwXQWo4o22eN50PNnlkc/Qs=", force_purepython=True, unicode_pw=True)

    @unittest.skipUnless(can_load_protobuf(), "requires protobuf")
    @unittest.skipUnless(can_load_scrypt(),   "requires a binary implementation of pylibscrypt")
    def test_bitcoinj_pp(self):
        self.key_tester("Ymo6MacXiCd1+6/qtPc5rCaj6qIGJbu5tX2PXQXqF4Df/kFrjNGMDMHqrwBAAAAIAAEAZwdBow==", force_purepython=True)
    #
    @unittest.skipUnless(tstr == unicode, "Unicode builds only")
    @unittest.skipUnless(can_load_protobuf(), "requires protobuf")
    @unittest.skipUnless(can_load_scrypt(),   "requires a binary implementation of pylibscrypt")
    def test_bitcoinj_unicode_pp(self):
        self.key_tester("Ymo6hgWTejxVYfL/LLF4af8j2RfEsi5y16kTQhECWnn9iCt8AmGWPoPomQBAAAAIAAEAfNRA3A==", force_purepython=True, unicode_pw=True)

    @unittest.skipUnless(can_load_scrypt(), "requires a binary implementation of pylibscrypt")
    def test_bither_pp(self):
        self.key_tester("YnQ6PocfHvWGVbCzlVb9cUtPDjosnuB7RoyspTEzZZAqURlCsLudQaQ4IkIW8YE=", force_purepython=True)
    #
    @unittest.skipUnless(tstr == unicode, "Unicode builds only")
    @unittest.skipUnless(can_load_scrypt(), "requires a binary implementation of pylibscrypt")
    def test_bither_unicode_pp(self):
        self.key_tester("YnQ6ENNU1KSJlzC8FMfAq/MHgWgaZkxpiByt/vLQ/UdP2NlCsLudQaQ4IjTbPcw=", force_purepython=True, unicode_pw=True)

    def test_msigna_pp(self):
        self.key_tester("bXM6SWd6U+qTKOzQDfz8auBL1/tzu0kap7NMOqctt7U0nA8XOI6j6BCjxCsc7mU=", force_purepython=True)
    #
    @unittest.skipUnless(tstr == unicode, "Unicode builds only")
    def test_msigna_unicode_pp(self):
        self.key_tester("bXM6i9OkMzrIJqWvpM+Dxq795jeFFxiB6DtBwuGmeEtfHLLOjMvoJRAWeSsf+Pg=", force_purepython=True, unicode_pw=True)

    def test_electrum_pp(self):
        self.key_tester("ZWw6kLJxTDF7LxneT7c5DblJ9k9WYwV6YUIUQO+IDiIXzMUZvsCT", force_purepython=True)
    #
    @unittest.skipUnless(tstr == unicode, "Unicode builds only")
    def test_electrum_unicode_pp(self):
        self.key_tester("ZWw6rLwP/stP422FgteriIgvq4LD90adedrAqz61gKuYDRrx3+Q+", force_purepython=True, unicode_pw=True)

    def test_electrum2_pp(self):
        self.key_tester("ZTI69B961mYKYFV7Bg1zRYZ8ZGw4cE+2D8NF3lp6d2XPe8qTdJUz", force_purepython=True)
    #
    @unittest.skipUnless(tstr == unicode, "Unicode builds only")
    def test_electrum2_unicode_pp(self):
        self.key_tester("ZTI6k2tz83Lzs83hyQPRj2g90f7nVYHYM20qLv4NIVIzUNNqVWv8", force_purepython=True, unicode_pw=True)

    def test_blockchain_v0_pp(self):
        self.key_tester("Yms69Z9y1J66ceYKkrXy11mHR+YDD8WrPJeTNaAnO7LO7YgAAAAAbnp7YQ==", force_purepython=True, force_kdf_purepython=True)
    #
    @unittest.skipUnless(tstr == unicode, "Unicode builds only")
    def test_blockchain_v0_unicode_pp(self):
        self.key_tester("Yms68OsennSoypcGGUvhrhEBFCiIkAK2Qphnfdc3Ungk/SoAAAAAcr6jYQ==", force_purepython=True, force_kdf_purepython=True, unicode_pw=True)

    def test_blockchain_v2_pp(self):
        self.key_tester("Yms6abF6aZYdu5sKpStKA4ihra6GEAeZTumFiIM0YQUkTjcQJwAAj8ekAQ==", force_purepython=True, force_kdf_purepython=True)

    def test_blockchain_secondpass_pp(self):                # extracted from blockchain-v0.0-wallet.aes.json which has a second password iter_count
        self.key_tester("YnM6ujsYxz3SE7fEEekfMuIC1oII7KY//j5FMObBn7HydqVyjnaeTCZDAaC4LbJcVkxaCgAAACsWXkw=", force_kdf_purepython=True)
    #
    @unittest.skipUnless(tstr == unicode, "Unicode builds only")
    def test_blockchain_secondpass_unicode_pp(self):
        self.key_tester("YnM6/e8Inpbesj+CYE0YvdXLewgN5UH9KFvliZrI43OmYnyHbCa71RBD57XO0CbuADDTCgAAACCVL/w=", force_kdf_purepython=True, unicode_pw=True)

    def test_blockchain_secondpass_no_iter_count_pp(self):  # extracted from blockchain-unencrypted-wallet.aes.json which is missing a second password iter_count
        self.key_tester("YnM6ujsYxz3SE7fEEekfMuIC1oII7KY//j5FMObBn7HydqVyjnaeTCZDAaC4LbJcVkxaAAAAAE/24yM=", force_kdf_purepython=True)

    @unittest.skipUnless(has_any_opencl_devices(), "requires OpenCL and a compatible device")
    def test_bitcoincore_cl(self):
        btcrecover.load_from_base64_key("YmM65iRhIMReOQ2qaldHbn++T1fYP3nXX5tMHbaA/lqEbLhFk6/1Y5F5x0QJAQBI/maR")

        dev_names_tested = set()
        for dev in btcrecover.get_opencl_devices():
            if dev.name in dev_names_tested: continue
            dev_names_tested.add(dev.name)
            btcrecover.loaded_wallet.init_opencl_kernel([dev], [4], [4], 200)

            self.assertEqual(btcrecover.return_verified_password_or_false(
                ["btcr-wrong-password-1", "btcr-wrong-password-2"]), (False, 2),
                dev.name.strip() + " found a false positive")
            self.assertEqual(btcrecover.return_verified_password_or_false(
                ["btcr-wrong-password-3", "btcr-test-password", "btcr-wrong-password-4"]), ("btcr-test-password", 2),
                dev.name.strip() + " failed to find password")

    @unittest.skipUnless(tstr == unicode, "Unicode builds only")
    @unittest.skipUnless(has_any_opencl_devices(), "requires OpenCL and a compatible device")
    def test_bitcoincore_cl_unicode(self):
        btcrecover.load_from_base64_key("YmM6XAL2X19VfzlKJfc+7LIeNrB2KC8E9DWe1YhhOchPoClvwftbuqjXKkfdAAARmggo")

        dev_names_tested = set()
        for dev in btcrecover.get_opencl_devices():
            if dev.name in dev_names_tested: continue
            dev_names_tested.add(dev.name)
            btcrecover.loaded_wallet.init_opencl_kernel([dev], [4], [4], 200)

            self.assertEqual(btcrecover.return_verified_password_or_false(
                ["btcr-wrong-password-3", "btcr-тест-пароль", "btcr-wrong-password-4"]), ("btcr-тест-пароль", 2),
                dev.name.strip() + " failed to find password")

    @unittest.skipUnless(has_any_opencl_devices(), "requires OpenCL and a compatible device")
    @unittest.skipIf(sys.platform == "win32", "windows kills and restarts drivers which take too long")
    def test_bitcoincore_cl_no_interrupts(self):
        btcrecover.load_from_base64_key("YmM65iRhIMReOQ2qaldHbn++T1fYP3nXX5tMHbaA/lqEbLhFk6/1Y5F5x0QJAQBI/maR")

        dev_names_tested = set()
        for dev in btcrecover.get_opencl_devices():
            if dev.name in dev_names_tested: continue
            dev_names_tested.add(dev.name)
            btcrecover.loaded_wallet.init_opencl_kernel([dev], [4], [4], 1)

            self.assertEqual(btcrecover.return_verified_password_or_false(
                ["btcr-wrong-password-1", "btcr-wrong-password-2"]), (False, 2))
            self.assertEqual(btcrecover.return_verified_password_or_false(
                ["btcr-wrong-password-3", "btcr-test-password", "btcr-wrong-password-4"]), ("btcr-test-password", 2))

    @unittest.skipUnless(has_any_opencl_devices(), "requires OpenCL and a compatible device")
    def test_bitcoincore_cl_sli(self):
        devices_by_name = dict()
        for dev in btcrecover.get_opencl_devices():
            if dev.name in devices_by_name: break
            else: devices_by_name[dev.name] = dev
        else:
            self.skipTest("requires two identical OpenCL devices")

        btcrecover.load_from_base64_key("YmM65iRhIMReOQ2qaldHbn++T1fYP3nXX5tMHbaA/lqEbLhFk6/1Y5F5x0QJAQBI/maR")
        btcrecover.loaded_wallet.init_opencl_kernel([devices_by_name[dev.name], dev], [2, 2], [2, 2], 200)

        self.assertEqual(btcrecover.return_verified_password_or_false(
            ["btcr-wrong-password-1", "btcr-wrong-password-2", "btcr-wrong-password-3", "btcr-wrong-password-4"]), (False, 4))
        self.assertEqual(btcrecover.return_verified_password_or_false(
            ["btcr-wrong-password-5", "btcr-test-password", "btcr-wrong-password-6"]), ("btcr-test-password", 2))
        self.assertEqual(btcrecover.return_verified_password_or_false(
            ["btcr-wrong-password-5", "btcr-wrong-password-6", "btcr-test-password"]), ("btcr-test-password", 3))

    @unittest.skipUnless(can_load_armory(), "requires Armory and ASCII version of btcrecover")
    @unittest.skipUnless(has_any_opencl_devices(), "requires OpenCL and a compatible device")
    def test_armory_cl(self):
        btcrecover.load_from_base64_key("YXI6r7mks1qvph4G+rRT7WlIptdr9qDqyFTfXNJ3ciuWJ12BgWX5Il+y28hLNr/u4Wl49hUi4JBeq6Jz9dVBX3vAJ6476FEAACAABAAAAGGwnwXRpPbBzC5lCOBVVWDu7mUJetBOBvzVAv0IbrboDXqA8A==")

        dev_names_tested = set()
        for dev in btcrecover.get_opencl_devices():
            if dev.name in dev_names_tested: continue
            dev_names_tested.add(dev.name)
            btcrecover.loaded_wallet.init_opencl_kernel([dev], [4], [4], 200)

            self.assertEqual(btcrecover.return_verified_password_or_false(
                ["btcr-wrong-password-1", "btcr-wrong-password-2"]), (False, 2),
                dev.name.strip() + " found a false positive")
            self.assertEqual(btcrecover.return_verified_password_or_false(
                ["btcr-wrong-password-3", "btcr-test-password", "btcr-wrong-password-4"]), ("btcr-test-password", 2),
                dev.name.strip() + " failed to find password")

    @unittest.skipUnless(can_load_armory(), "requires Armory and ASCII version of btcrecover")
    @unittest.skipUnless(has_any_opencl_devices(), "requires OpenCL and a compatible device")
    def test_armory_cl_mem_factor(self):
        btcrecover.load_from_base64_key("YXI6r7mks1qvph4G+rRT7WlIptdr9qDqyFTfXNJ3ciuWJ12BgWX5Il+y28hLNr/u4Wl49hUi4JBeq6Jz9dVBX3vAJ6476FEAACAABAAAAGGwnwXRpPbBzC5lCOBVVWDu7mUJetBOBvzVAv0IbrboDXqA8A==")

        dev_names_tested = set()
        for dev in btcrecover.get_opencl_devices():
            if dev.name in dev_names_tested: continue
            dev_names_tested.add(dev.name)
            btcrecover.loaded_wallet.init_opencl_kernel([dev], [8], [8], 200, save_every=3)

            self.assertEqual(btcrecover.return_verified_password_or_false(
                ["btcr-wrong-password-1", "btcr-wrong-password-2"]), (False, 2),
                dev.name.strip() + " found a false positive")
            self.assertEqual(btcrecover.return_verified_password_or_false(
                ["btcr-wrong-password-3", "btcr-test-password", "btcr-wrong-password-4"]), ("btcr-test-password", 2),
                dev.name.strip() + " failed to find password")

    @unittest.skipUnless(can_load_armory(), "requires Armory and ASCII version of btcrecover")
    @unittest.skipUnless(has_any_opencl_devices(), "requires OpenCL and a compatible device")
    @unittest.skipIf(sys.platform == "win32", "windows kills and restarts drivers which take too long")
    def test_armory_cl_no_interrupts(self):
        btcrecover.load_from_base64_key("YXI6r7mks1qvph4G+rRT7WlIptdr9qDqyFTfXNJ3ciuWJ12BgWX5Il+y28hLNr/u4Wl49hUi4JBeq6Jz9dVBX3vAJ6476FEAACAABAAAAGGwnwXRpPbBzC5lCOBVVWDu7mUJetBOBvzVAv0IbrboDXqA8A==")

        dev_names_tested = set()
        for dev in btcrecover.get_opencl_devices():
            if dev.name in dev_names_tested: continue
            dev_names_tested.add(dev.name)
            btcrecover.loaded_wallet.init_opencl_kernel([dev], [4], [4], 1)

            self.assertEqual(btcrecover.return_verified_password_or_false(
                ["btcr-wrong-password-1", "btcr-wrong-password-2"]), (False, 2))
            self.assertEqual(btcrecover.return_verified_password_or_false(
                ["btcr-wrong-password-3", "btcr-test-password", "btcr-wrong-password-4"]), ("btcr-test-password", 2))

    @unittest.skipUnless(can_load_armory(), "requires Armory and ASCII version of btcrecover")
    @unittest.skipUnless(has_any_opencl_devices(), "requires OpenCL and a compatible device")
    def test_armory_cl_sli(self):
        devices_by_name = dict()
        for dev in btcrecover.get_opencl_devices():
            if dev.name in devices_by_name: break
            else: devices_by_name[dev.name] = dev
        else:
            self.skipTest("requires two identical OpenCL devices")

        btcrecover.load_from_base64_key("YXI6r7mks1qvph4G+rRT7WlIptdr9qDqyFTfXNJ3ciuWJ12BgWX5Il+y28hLNr/u4Wl49hUi4JBeq6Jz9dVBX3vAJ6476FEAACAABAAAAGGwnwXRpPbBzC5lCOBVVWDu7mUJetBOBvzVAv0IbrboDXqA8A==")
        btcrecover.loaded_wallet.init_opencl_kernel([devices_by_name[dev.name], dev], [4, 4], [4, 4], 200)

        self.assertEqual(btcrecover.return_verified_password_or_false(
            ["btcr-wrong-password-1", "btcr-wrong-password-2", "btcr-wrong-password-3", "btcr-wrong-password-4",
             "btcr-wrong-password-5", "btcr-wrong-password-6", "btcr-wrong-password-7", "btcr-wrong-password-8"]), (False, 8))
        self.assertEqual(btcrecover.return_verified_password_or_false(
            ["btcr-wrong-password-1", "btcr-wrong-password-2", "btcr-test-password",    "btcr-wrong-password-4",
             "btcr-wrong-password-5", "btcr-wrong-password-6", "btcr-wrong-password-7", "btcr-wrong-password-8"]), ("btcr-test-password", 3))
        self.assertEqual(btcrecover.return_verified_password_or_false(
            ["btcr-wrong-password-1", "btcr-wrong-password-2", "btcr-wrong-password-3", "btcr-wrong-password-4",
             "btcr-wrong-password-5", "btcr-wrong-password-6", "btcr-wrong-password-7", "btcr-test-password"]), ("btcr-test-password", 8))

    def test_invalid_crc(self):
        with self.assertRaises(SystemExit) as cm:
            self.key_tester("aWI6oikebfNQTLk75CfI5X3svX6AC7NFeGsgTNXZfA==")
        self.assertIn("encrypted key data is corrupted (failed CRC check)", cm.exception.code)


E2E_ARGS = b"--tokenlist __funccall --exclude-passwordlist __funccall --data-extract --autosave __funccall " \
           b"--typos 3 --typos-case --typos-repeat --typos-swap --no-progress".split()
E2E_TOKENLIST    = "+ ^%0,1[b-c]tcr-- \n"  "+ ^,$%0,1<Test- \n"  "^3$pas \n"  "+ wrod$"
E2E_EXCLUDELIST  = "tCr--Test-wrod\n" "btcr-Tsett-paaswrod\n" "ctcr--Test-pAssrwod"  # passwords #4, #100004, & #120004
E2E_DATA_EXTRACT = "bWI6oikebfNQTLk75CfI5X3svX6AC7NFeGsgTNXZfA=="
class Test09EndToEnd(unittest.TestCase):

    autosave_file = BytesIONonClosing()

    # These test_ functions are in alphabetical order (the same order they're executed in)

    # A test of multiple features at once
    def test_end_to_end(self):
        autosave_file = self.__class__.autosave_file
        btcrecover.parse_arguments(E2E_ARGS,
            tokenlist            = StringIO(E2E_TOKENLIST),
            exclude_passwordlist = StringIO(E2E_EXCLUDELIST),
            data_extract         = E2E_DATA_EXTRACT,
            autosave             = autosave_file)
        self.assertEqual("btcr-test-password", btcrecover.main()[0])

        # Verify the exact password number where it was found to ensure password ordering hasn't changed
        autosave_file.seek(SAVESLOT_SIZE)
        savestate = cPickle.load(autosave_file)
        self.assertEqual(savestate.get(b"skip"), 103762)

    # Repeat the test above using the same autosave file, starting off just before the password was found
    def test_restore(self):
        self.test_end_to_end()

        # Verify the password number where the search started
        autosave_file = self.__class__.autosave_file
        autosave_file.seek(0)
        savestate = cPickle.load(autosave_file)
        self.assertEqual(savestate.get(b"skip"), 103762)

    # Repeat the first test with a new autosave file, using --skip to start just after the password is located
    def test_skip(self):
        autosave_file = BytesIONonClosing()
        btcrecover.parse_arguments(E2E_ARGS + [b"--skip=103763"],
            tokenlist            = StringIO(E2E_TOKENLIST),
            exclude_passwordlist = StringIO(E2E_EXCLUDELIST),
            data_extract         = E2E_DATA_EXTRACT,
            autosave             = autosave_file)
        self.assertIn("Password search exhausted", btcrecover.main()[1])

        # Verify the password number where the search started
        autosave_file.seek(0)
        savestate = cPickle.load(autosave_file)
        self.assertEqual(savestate.get(b"skip"), 103763)

        # Verify the total count of passwords
        autosave_file.seek(SAVESLOT_SIZE)
        savestate = cPickle.load(autosave_file)
        self.assertEqual(savestate.get(b"skip"), 139652)


# QuickTests: all of Test01Basics, Test02Anchors, Test03WildCards, and Test04Typos,
# all of Test05CommandLine except the "large" tests, and select quick tests from
# Test08KeyDecryption
class QuickTests(unittest.TestSuite) :
    def __init__(self):
        super(QuickTests, self).__init__()
        tl = unittest.defaultTestLoader
        self.addTests(tl.loadTestsFromTestCase(TestCase)
            for TestCase in (Test01Basics, Test02Anchors, Test03WildCards, Test04Typos))
        self.addTest(tl.loadTestsFromNames(("Test05CommandLine." + method_name
            for method_name in tl.getTestCaseNames(Test05CommandLine) if "large" not in method_name),
            module=sys.modules[__name__]))
        self.addTest(tl.loadTestsFromNames(("Test08KeyDecryption." + method_name
            for method_name in (
                "test_bitcoincore_pp",
                "test_bitcoincore_unicode_pp",
                "test_multibit",
                "test_multibit_unicode",
                "test_multidoge",
                "test_multidoge_unicode",
                "test_androidwallet",
                "test_androidwallet_unicode",
                "test_androidknc",
                "test_androidknc_unicode",
                "test_multibithd",
                "test_multibithd_unicode",
                "test_bitcoinj",
                "test_bitcoinj_unicode",
                "test_bither",
                "test_bither_unicode",
                "test_msigna",
                "test_msigna_unicode",
                "test_electrum",
                "test_electrum_unicode",
                "test_electrum2",
                "test_electrum2_unicode",
                "test_blockchain_v0",
                "test_blockchain_v0_unicode",
                "test_blockchain_v2",
                "test_blockchain_secondpass",
                "test_blockchain_secondpass_unicode",
                "test_blockchain_secondpass_no_iter_count",
                "test_multibit_pp",
                "test_multibit_unicode_pp",
                "test_multidoge_pp",
                "test_multidoge_unicode_pp",
                "test_androidwallet_pp",
                "test_androidwallet_unicode_pp",
                "test_androidknc_pp",
                "test_androidknc_unicode_pp",
                "test_multibithd_pp",
                "test_multibithd_unicode_pp",
                "test_bitcoinj_pp",
                "test_bitcoinj_unicode_pp",
                "test_bither_pp",
                "test_bither_unicode_pp",
                "test_msigna_pp",
                "test_msigna_unicode_pp",
                "test_electrum_pp",
                "test_electrum_unicode_pp",
                "test_electrum2_pp",
                "test_electrum2_unicode_pp",
                "test_blockchain_v0_pp",
                "test_blockchain_v0_unicode_pp",
                "test_blockchain_secondpass_pp",
                "test_blockchain_secondpass_unicode_pp",
                "test_blockchain_secondpass_no_iter_count_pp",
                "test_invalid_crc")),
            module=sys.modules[__name__]
        ))
        self.addTests(tl.loadTestsFromTestCase(Test08BIP39Passwords))


if __name__ == b'__main__':

    import argparse, atexit

    # Add two new arguments to those already provided by unittest.main()
    parser = argparse.ArgumentParser(add_help=False)
    parser.add_argument("--no-buffer", action="store_true")
    parser.add_argument("--no-pause",  action="store_true")
    args, unittest_args = parser.parse_known_args()
    sys.argv[1:] = unittest_args

    # By default, pause before exiting
    if not args.no_pause:
        atexit.register(lambda: raw_input("\nPress Enter to exit ..."))

    unittest.main(buffer = not args.no_buffer)
