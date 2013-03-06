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
"""Testing Support
"""
import os
import pymongo
import m01.mongofake

# mongo db name used for testing
TEST_DB_NAME = 'm01_mongofake_database'

###############################################################################
#
# test helper methods
#
###############################################################################

_testClient = None

def getTestClient():
    return _testClient


def getTestDatabase():
    client = getTestClient()
    return client[TEST_DB_NAME]


def getTestCollection(collectionName='test'):
    client = getTestClient()
    db = client[TEST_DB_NAME]
    return db[collectionName]


def dropTestDatabase():
    client = getTestClient()
    client.drop_database(TEST_DB_NAME)


###############################################################################
#
# test setup methods
#
###############################################################################

# fake mongodb setup
def setUpFakeMongo(test=None):
    """Setup fake (singleton) mongo client"""
    global _testClient
    host = 'localhost'
    port = 45017
    _testClient = m01.mongofake.fakeMongoClient(host, port)


def tearDownFakeMongo(test=None):
    """Tear down fake mongo client"""
    global _testClient
    _testClient = None


# stub mongodb server
def setUpStubMongo(test=None):
    """Setup real empty mongodb"""
    host = 'localhost'
    port = 45017
    sandBoxDir = os.path.join(os.path.dirname(__file__), 'sandbox')
    import m01.stub.testing
    m01.stub.testing.startMongoDBServer(host, port, sandBoxDir=sandBoxDir)
    # ensure that we use a a real MongoClient
    global _testClient
    _testClient = pymongo.MongoClient(host, port)


def tearDownStubMongo(test=None):
    """Tear down real mongodb"""
    sleep = 0.5
    import m01.stub.testing
    m01.stub.testing.stopMongoDBServer(sleep)
