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
$Id$
"""
__docformat__ = "reStructuredText"

import re
import unittest
import doctest

from zope.testing.renormalizing import RENormalizing

import m01.mongofake.testing


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
    for name in testNames:
        suite = unittest.TestSuite((
            doctest.DocFileSuite(name,
                setUp=m01.mongofake.testing.setUpStubMongo,
                tearDown=m01.mongofake.testing.tearDownStubMongo,
                optionflags=doctest.NORMALIZE_WHITESPACE|doctest.ELLIPSIS,
                checker=CHECKER),
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
                checker=FAKE_CHECKER),
        )

    # additional non mongodb tests
    append(
        doctest.DocFileSuite('README.txt',
            optionflags=doctest.NORMALIZE_WHITESPACE|doctest.ELLIPSIS),
    )

    # return test suite
    return unittest.TestSuite(suites)


if __name__=='__main__':
    unittest.main(defaultTest='test_suite')
