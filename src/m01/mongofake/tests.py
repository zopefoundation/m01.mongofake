##############################################################################
#
# Copyright (c) 2012 Zope Foundation and Contributors.
# All Rights Reserved.
#
# This software is subject to the provisions of the Zope Public License,
# Version 2.1 (ZPL).  A copy of the ZPL should accompany this distribution.
# THIS SOFTWARE IS PROVIDED "AS IS" AND ANY AND ALL EXPRESS OR IMPLIED
# WARRANTIES ARE DISCLAIMED, INCLUDING, BUT NOT LIMITED TO, THE IMPLIED
# WARRANTIES OF TITLE, MERCHANTABILITY, AGAINST INFRINGEMENT, AND FITNESS
# FOR A PARTICULAR PURPOSE.
#
##############################################################################
"""
"""
import re
import unittest
import doctest

from zope.testing.renormalizing import RENormalizing

import m01.mongofake.testing

try:
    import m01.stub
except ImportError:
    has_m01_stub = False
else:
    has_m01_stub = True

PY_COMPAT = RENormalizing([
    # Python 3 unicode removed the "u".
    (re.compile("u('.*?')"),
     r"\1"),
    (re.compile('u(".*?")'),
     r"\1"),
    # Python 3 adds module.
    (re.compile('datetime.datetime'),
     r"datetime"),
   ])

CHECKER = RENormalizing([
   (re.compile('connectionId'), '...'),
   ])


FAKE_CHECKER = RENormalizing([
   (re.compile('FakeMongoClient'), 'MongoClient'),
   (re.compile('FakeDatabase'), 'Database'),
   (re.compile('FakeCollection'), 'Collection'),
   (re.compile("'connectionId': [0-9]+"), r"'connectionId': ..."),
   ])


def test_suite():
    """This test suite will run the tests with the fake and a real mongodb and
    make sure both output are the same.
    """
    suites = []
    append = suites.append

    # real mongo database tests using m01.stub using level 2 tests (--all)
    testNames = ['testing.txt',
                 ]
    if has_m01_stub:
        for name in testNames:
            suite = unittest.TestSuite((
                doctest.DocFileSuite(name,
                    setUp=m01.mongofake.testing.setUpStubMongo,
                    tearDown=m01.mongofake.testing.tearDownStubMongo,
                    optionflags=doctest.NORMALIZE_WHITESPACE|doctest.ELLIPSIS,
                    checker=PY_COMPAT+CHECKER),
                ))
            suite.level = 2
            append(suite)

    # fake mongo database tests using FakeMongoClient
    for name in testNames:
        append(
            doctest.DocFileSuite(name,
                setUp=m01.mongofake.testing.setUpFakeMongo,
                tearDown=m01.mongofake.testing.tearDownFakeMongo,
                optionflags=doctest.NORMALIZE_WHITESPACE|doctest.ELLIPSIS,
                checker=PY_COMPAT+FAKE_CHECKER),
        )

    # additional non mongodb tests
    append(
        doctest.DocFileSuite(
            'README.txt',
            checker=PY_COMPAT,
            optionflags=doctest.NORMALIZE_WHITESPACE|doctest.ELLIPSIS),
    )

    # return test suite
    return unittest.TestSuite(suites)


if __name__=='__main__':
    unittest.main(defaultTest='test_suite')
