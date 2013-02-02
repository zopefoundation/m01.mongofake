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

import calendar
import copy
import pprint as pp
import re
import struct
import time
import types

import bson.objectid
import bson.son
import pymongo.cursor
import pymongo.database


###############################################################################
#
# test helper methods
#
###############################################################################

# SON to dict converter
def dictify(data):
    """Recursive replace SON items with dict in the given data structure.

    Compared to the SON.to_dict method, this method will also handle tuples
    and keep them intact.

    """
    if isinstance(data, bson.son.SON):
        data = dict(data)
    if isinstance(data, dict):
        d = {}
        for k, v in data.iteritems():
            # replace nested SON items
            d[k] = dictify(v)
    elif isinstance(data, (tuple, list)):
        d = []
        for v in data:
            # replace nested SON items
            d.append(dictify(v))
        if isinstance(data, tuple):
            # keep tuples intact
            d = tuple(d)
    else:
        d = data
    return d


def pprint(data):
    """Can pprint a bson.son.SON instance like a dict"""
    pp.pprint(dictify(data))


class RENormalizer(object):
    """Normalizer which can convert text based on regex patterns"""

    def __init__(self, patterns):
        self.patterns = patterns
        self.transformers = map(self._cook, patterns)

    def _cook(self, pattern):
        if callable(pattern):
            return pattern
        regexp, replacement = pattern
        return lambda text: regexp.sub(replacement, text)

    def addPattern(self, pattern):
        patterns = list(self.patterns)
        patterns.append(pattern)
        self.transformers = map(self._cook, patterns)
        self.patterns = patterns

    def __call__(self, data):
        """Recursive normalize a SON instance, dict or text"""
        if not isinstance(data, basestring):
            data = pp.pformat(dictify(data))
        for normalizer in self.transformers:
            data = normalizer(dictify(data))
        return data

    def pprint(self, data):
        """Pretty print data"""
        if isinstance(data, pymongo.cursor.Cursor):
            for item in data:
                print self(item)
        else:
            print self(data)


# see testing.txt for a sample usage
reNormalizer = RENormalizer([
   (re.compile(u"(\d\d\d\d)-(\d\d)-(\d\d)[tT](\d\d):(\d\d):(\d\d)"),
               r"NNNN-NN-NNTNN:NN:NN"),
   (re.compile(u"(\d\d\d\d)-(\d\d)-(\d\d) (\d\d):(\d\d):(\d\d)"),
               r"NNNN-NN-NN NN:NN:NN"),
   (re.compile("ObjectId\(\'[a-zA-Z0-9]+\'\)"), r"ObjectId('...')"),
   (re.compile("Timestamp\([a-zA-Z0-9, ]+\)"), r"Timestamp('...')"),
   (re.compile("datetime.datetime\([a-zA-Z0-9, ]+tzinfo=<bson.tz_util.FixedOffset[a-zA-Z0-9 ]+>\)"),
               "datetime(..., tzinfo=<bson.tz_util.FixedOffset ...>)"),
   (re.compile("datetime.datetime\([a-zA-Z0-9, ]+tzinfo=[a-zA-Z0-9>]+\)"),
               "datetime(..., tzinfo= ...)"),
   (re.compile("datetime\([a-z0-9, ]+\)"), "datetime(...)"),
   (re.compile("object at 0x[a-zA-Z0-9]+"), "object at ..."),
   ])


def getObjectId(secs=0):
    """Knows how to generate similar ObjectId based on integer (counter)

    Note: this method can get used if you need to define similar ObjectId
    in a non persistent environment if need to bootstrap mongo containers.
    """
    time_tuple = time.gmtime(secs)
    ts = calendar.timegm(time_tuple)
    oid = struct.pack(">i", int(ts)) + "\x00" * 8
    return bson.objectid.ObjectId(oid)


def getObjectIdByTimeStr(tStr, format="%Y-%m-%d %H:%M:%S"):
    """Knows how to generate similar ObjectId based on a time string

    The time string format used by default is ``%Y-%m-%d %H:%M:%S``.
    Use the current development time which could prevent duplicated
    ObjectId. At least some kind of ;-)
    """
    time.strptime(tStr, "%Y-%m-%d %H:%M:%S")
    ts = time.mktime(tStr)
    oid = struct.pack(">i", int(ts)) + "\x00" * 8
    return bson.objectid.ObjectId(oid)


###############################################################################
#
# fake MongoDB
#
###############################################################################

class OrderedData(object):
    """Ordered data."""

    def __init__(self):
        self.data = {}
        self._order = []

    def __len__(self):
        return len(self.data)

    def __contains__(self, key):
        return key in self.data

    def __getitem__(self, key):
        return self.data[key]

    def __setitem__(self, key, item):
        if key not in self._order:
            self._order.append(key)
        self.data[key] = copy.deepcopy(item)

    def __delitem__(self, key):
        del self.data[key]
        self._order.remove(key)

    def get(self, key, default=None):
        """Get item by key"""
        return self.data.get(key, default)

    def keys(self):
        return self._order

    def values(self):
        for key in self._order:
            return self.data[key]

    def items(self):
        for key in self._order:
            yield (key, self.data[key])

    def __iter__(self):
        for key in self._order:
            yield self.data[key]

    def __repr__(self):
        return repr(self.data.values())


def sortByAttribute(name, order):
    def sort(d1, d2):
        v1 = d1.get(name, None)
        v2 = d2.get(name, None)
        try:
            res = cmp(v1, v2)
        except TypeError:
            res = -1
        if order:
            return res
        else:
            return -res
    return sort


def cursor_comparator(keys):
    def comparator(a, b):
        for k, d in keys:
            part = cmp(a.get(k), b.get(k))
            if part:
                return part * d
        return 0
    return comparator

NOVALUEMARKER = object()


def getPart(doc, k):
    parts = k.split('.')

    def getP(doc, part):
        try:
            # try an attribute
            return getattr(doc, part)
        except AttributeError:
            try:
                # try a dict
                return doc[part]
            except TypeError:
                try:
                    # try a sequence
                    return doc[int(part)]
                except:
                    pass
        return NOVALUEMARKER

    d = doc
    for p in parts:
        prevD = d
        d = getP(d, p)
        if d == NOVALUEMARKER:
            #if it starts with '$' try again without $, like for $id
            if p.startswith('$'):
                d = getP(prevD, p[1:])
                if d == NOVALUEMARKER:
                    return d
    return d


class FakeCursor(object):
    """Fake mongoDB cursor."""

    def __init__(self, collection, spec, fields, skip, limit, slave_okay,
                 timeout, tailable, snapshot=False, sort=None,
                 _sock=None, _must_use_master=False):
        # filter and setup docs based on given spec
        self.collection = collection
        self._skip = skip
        self._limit = limit
        self.docs = self._query(collection, spec, sort)
        self.total = len(self.docs)

    def _query(self, collection, spec, sort=None):
        docs = []
        append = docs.append
        for key, doc in collection.docs.items():
            for k, v in spec.items():
                if k in doc and isinstance(v, dict):
                    reject = False
                    for op, value in v.items():
                        if ((op == '$gt' and not doc[k] > value) or
                            (op == '$lt' and not doc[k] < value) or
                            (op == '$gte' and not doc[k] >= value) or
                            (op == '$lte' and not doc[k] <= value) or
                            (op == '$ne' and not doc[k] != value) or
                            (op == '$in' and not doc[k] in value) or
                            (op == '$exists' and not k in doc) or
                            (op == '$all' and not all([vv in doc[k]
                                                       for vv in value])) or
                            (op == '$nin' and not doc[k] not in value)
                            # TODO: $mod, $nor $or, $and, $size, $type, $regex
                            ):
                            reject = True
                            break
                    if reject:
                        break
                else:
                    if '.' in k:
                        # support diving into attributes/documents
                        docVal = getPart(doc, k)
                    else:
                        # Mongo always ignores documents where a key of the
                        # spec is missing.
                        if k not in doc:
                            break
                        docVal = doc.get(k, NOVALUEMARKER)
                    # XXX: This is not generic and will not handle operator
                    # based specs.
                    if docVal != NOVALUEMARKER and v != docVal:
                        break
            else:
                append(copy.deepcopy(doc))

        if sort:
            docs = sorted(docs, cmp=cursor_comparator(sort))

        return docs

    def count(self, with_limit_and_skip=False):
        if with_limit_and_skip:
            return len(self.docs)
        else:
            return self.total

    def skip(self, skip):
        self._skip = skip
        self.docs = self.docs[skip:]
        return self

    def limit(self, limit):
        self._limit = limit
        self.docs = self.docs[:limit]
        return self

    def sort(self, name, order):
        sorter = sortByAttribute(name, order)
        docs = list(self.docs)
        docs.sort(sorter)
        self.docs = docs
        return self

    def __iter__(self):
        return self

    def next(self):
        if len(self.docs):
            next = self.docs.pop(0)
        else:
            raise StopIteration
        return next


class FakeCollection(object):
    """Fake mongoDB collection"""

    def __init__(self, database, name):
        self.database = database
        self.name = unicode(name)
        self.full_name = '%s.%s' % (database, name)
        self.docs = OrderedData()

    def __getattr__(self, name):
        """Get a sub-collection of this collection by name (e.g. gridfs)"""
        return FakeCollection(self.database, u"%s.%s" % (self.name, name))

    def clear(self):
        for k in self.docs.keys():
            del self.docs[k]

    def count(self):
        return len(self.docs)

    def update(self, spec, document, upsert=False, manipulate=False, safe=None,
        multi=False, check_keys=True, **kwargs):
        if not isinstance(spec, types.DictType):
            raise TypeError("spec must be an instance of dict")
        if not isinstance(document, types.DictType):
            raise TypeError("document must be an instance of dict")
        if not isinstance(upsert, types.BooleanType):
            raise TypeError("upsert must be an instance of bool")

        existing = False
        counter = 0
        for key, doc in list(self.docs.items()):
            if (counter > 0 and not multi):
                break
            for k, v in spec.items():
                if k in doc and v == doc[k]:
                    setData = document.get('$set')
                    if setData is not None:
                        # do a partial update based on $set data
                        for pk, pv in setData.items():
                            doc[unicode(pk)] = pv
                        counter += 1
                        existing = True
                    else:
                        d = {}
                        for k, v in list(document.items()):
                            # use unicode keys as mongodb does
                            d[unicode(k)] = v
                        self.docs[unicode(key)] = d
                        existing = True
                        counter += 1
                    break

        cid = 42
        ok = 1.0
        err = None
        return {u'updatedExisting': existing, u'connectionId': cid, u'ok': ok,
                u'err': err, u'n': counter}

    def save(self, to_save, manipulate=True, safe=None, check_keys=True,
        **kwargs):
        if not isinstance(to_save, types.DictType):
            raise TypeError("cannot save object of type %s" % type(to_save))

        if "_id" not in to_save:
            return self.insert(to_save, manipulate, safe)
        else:
            self.update({"_id": to_save["_id"]}, to_save, upsert=True,
                manipulate=manipulate, safe=safe, multi=multi,
                check_keys=check_keys, **kwargs)
            return to_save.get("_id", None)

    def insert(self, doc_or_docs, manipulate=True, safe=None, check_keys=True,
        continue_on_error=False, **kwargs):
        docs = doc_or_docs
        if isinstance(docs, types.DictType):
            docs = [docs]
        for doc in docs:
            oid = doc.get('_id')
            if oid is None:
                oid = bson.objectid.ObjectId()
                doc[u'_id'] = oid
            d = {}
            for k, v in list(doc.items()):
                # use unicode keys as mongodb does
                d[unicode(k)] = v
            self.docs[unicode(oid)] = d

        ids = [doc.get("_id", None) for doc in docs]
        return len(ids) == 1 and ids[0] or ids

    def ensure_index(self, key_or_list, direction=None, unique=False, ttl=300):
        # we do not need indexes
        pass

    def find_one(self, spec_or_object_id=None, fields=None, slave_okay=True,
        _sock=None, _must_use_master=False):
        spec = spec_or_object_id
        if spec is None:
            spec = bson.son.SON()
        if isinstance(spec, bson.objectid.ObjectId):
            spec = bson.son.SON({"_id": spec})

        for result in self.find(spec, limit=-1, fields=fields,
            slave_okay=slave_okay, _sock=_sock,
            _must_use_master=_must_use_master):
            return result
        return None

    def find(self, spec=None, fields=None, skip=0, limit=0, slave_okay=True,
        timeout=True, snapshot=False, tailable=False, sort=None, _sock=None,
        _must_use_master=False):
        if spec is None:
            spec = bson.son.SON()

        if not isinstance(spec, types.DictType):
            raise TypeError("spec must be an instance of dict")
        if not isinstance(fields, (
            types.ListType, types.TupleType, types.NoneType)):
            raise TypeError("fields must be an instance of list, tuple or None")
        if not isinstance(skip, types.IntType):
            raise TypeError("skip must be an instance of int")
        if not isinstance(limit, types.IntType):
            raise TypeError("limit must be an instance of int")
        if not isinstance(slave_okay, types.BooleanType):
            raise TypeError("slave_okay must be an instance of bool")
        if not isinstance(timeout, types.BooleanType):
            raise TypeError("timeout must be an instance of bool")
        if not isinstance(snapshot, types.BooleanType):
            raise TypeError("snapshot must be an instance of bool")
        if not isinstance(tailable, types.BooleanType):
            raise TypeError("tailable must be an instance of bool")

        if fields is not None:
            if not fields:
                fields = ["_id"]
            fields = self._fields_list_to_dict(fields)

        return FakeCursor(self, spec, fields, skip, limit, slave_okay, timeout,
                      tailable, snapshot, sort=sort, _sock=_sock,
                      _must_use_master=_must_use_master)

    def remove(self, spec_or_id=None, safe=False, **kwargs):
        spec = spec_or_id
        if isinstance(spec, bson.objectid.ObjectId):
            spec = {"_id": spec}

        if not isinstance(spec, types.DictType):
            raise TypeError("spec must be an instance of dict, not %s" %
                            type(spec))

        response = {"serverUsed": "localhost:27017",
                    "n": 0,
                    "connectionId": 42,
                    "wtime": 0,
                    "err": None,
                    "ok": 1.0}

        for doc in self.find(spec, fields=()):
            del self.docs[unicode(doc['_id'])]
            response['n'] += 1

        return response

    # helper methods
    def _fields_list_to_dict(self, fields):
        as_dict = OrderedData()
        for field in fields:
            if not isinstance(field, types.StringTypes):
                raise TypeError("fields must be a list of key names as "
                                "(string, unicode)")
            as_dict[field] = 1
        return as_dict

    def __repr__(self):
        return "%s(%r, %r)" % (self.__class__.__name__, self.database,
            self.name)


class FakeDatabase(object):
    """Fake mongoDB database."""

    def __init__(self, connection, name):
        pymongo.database._check_name(name)
        self.__name = unicode(name)
        self.__connection = connection
        self.cols = {}

    @property
    def connection(self):
        return self.__connection

    @property
    def name(self):
        return self.__name

    def clear(self):
        for k, col in self.cols.items():
            col.clear()
            del self.cols[k]

    def create_collection(self, name, **kw):
        return True

    def collection_names(self):
        return list(self.cols.keys())

    def __getattr__(self, name):
        col = self.cols.get(name)
        if col is None:
            col = FakeCollection(self, name)
            self.cols[name] = col
        return col

    def __getitem__(self, name):
        return self.__getattr__(name)

    def __iter__(self):
        return self

    def next(self):
        raise TypeError("'Database' object is not iterable")

    def __call__(self, *args, **kwargs):
        """This is only here so that some API misusages are easier to debug.
        """
        raise TypeError("'Database' object is not callable. If you meant to "
                        "call the '%s' method on a '%s' object it is "
                        "failing because no such method exists." % (
                            self.__name, self.__connection.__class__.__name__))

    def __repr__(self):
        return "%s(%r, %r)" % (self.__class__.__name__, self.__connection,
            self.__name)


class FakeMongoClient(object):
    """Fake MongoDB MongoClient."""

    HOST = 'localhost'
    POST = 27017

    __max_bson_size = 4 * 1024 * 1024

    def __init__(self):
        self.__dbs = {}
        self.__host = None
        self.__port = None
        self.__max_pool_size = 10
        self.__document_class = {}
        self.__tz_aware = False
        self.__nodes = []

    @property
    def dbs(self):
        return self.__dbs

    def __call__(self, host=None, port=None, max_pool_size=10,
        document_class=dict, tz_aware=False, _connect=True, **kwargs):
        if host is None:
            host = self.HOST
        if isinstance(host, basestring):
            host = [host]
        if port is None:
            port = self.PORT
        if not isinstance(port, int):
            raise TypeError("port must be an instance of int")

        self.__max_pool_size = max_pool_size
        self.__document_class = document_class
        self.__tz_aware = tz_aware

        seeds = set()
        username = None
        password = None
        db = None
        opts = {}
        for entity in host:
            if "://" in entity:
                if entity.startswith("mongodb://"):
                    res = pymongo.uri_parser.parse_uri(entity, port)
                    seeds.update(res["nodelist"])
                    username = res["username"] or username
                    password = res["password"] or password
                    db = res["database"] or db
                    opts = res["options"]
                else:
                    idx = entity.find("://")
                    raise pymongo.errors.InvalidURI("Invalid URI scheme: %s" % (
                        entity[:idx],))
            else:
                seeds.update(pymongo.uri_parser.split_hosts(entity, port))
        if not seeds:
            raise pymongo.errors.ConfigurationError(
                "need to specify at least one host")

        self.__nodes = seeds
        self.__host = None
        self.__port = None

        if _connect:
            # _connect=False is not supported yet because we need to implement
            # some fake host, port setup concept first
            try:
                self.__find_node(seeds)
            except pymongo.errors.AutoReconnect, e:
                # ConnectionFailure makes more sense here than AutoReconnect
                raise pymongo.errors.ConnectionFailure(str(e))

        return self

    def __find_node(self, seeds=None):
        # very simple find node implementation
        errors = []
        mongos_candidates = []
        candidates = seeds or self.__nodes.copy()
        for candidate in candidates:
            node, ismaster, isdbgrid, res_time = self.__try_node(candidate)
            return node

        # couldn't find a suitable host.
        self.disconnect()
        raise pymongo.errors.AutoReconnect(', '.join(errors))

    def __try_node(self, node):
        self.disconnect()
        self.__host, self.__port = node
        # return node and some fake data
        ismaster = True
        isdbgrid = False
        res_time = None
        return node, ismaster, isdbgrid, res_time

    @property
    def host(self):
        return self.__host

    @property
    def port(self):
        return self.__port

    @property
    def tz_aware(self):
        return self.__tz_aware

    @property
    def max_bson_size(self):
        return self.__max_bson_size

    @property
    def nodes(self):
        """List of all known nodes."""
        return self.__nodes

    def drop_database(self, name):
        db = self.__dbs.get(name)
        if db is not None:
            db.clear()
            del self.__dbs[name]

    def database_names(self):
        return list(self.__dbs.keys())

    def disconnect(self):
        pass

    def close(self):
        self.disconnect()

    def alive(self):
        return True

    def __getattr__(self, name):
        db = self.__dbs.get(name)
        if db is None:
            db = FakeDatabase(self, name)
            self.dbs[name] = db
        return db

    def __getitem__(self, name):
        return self.__getattr__(name)

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.disconnect()

    def __iter__(self):
        return self

    def next(self):
        raise TypeError("'%s' object is not iterable" % self.__class__.__name__)

    def __repr__(self):
        if len(self.__nodes) == 1:
            return "%s(%r, %r)" % (self.__class__.__name__, self.__host, self.__port)
        else:
            nodes = ["%s:%d" % n for n in self.__nodes]
            return "%s(%r)" % (self.__class__.__name__, nodes)


class FakeMongoConnection(FakeMongoClient):
    """BBB: support old FakeMongoConnection class"""


# single shared MongoClient instance
fakeMongoClient = FakeMongoClient()

# BBB: support
fakeMongoConnection = FakeMongoConnection()


class FakeMongoConnectionPool(object):
    """Fake mongodb connection pool."""

    def __init__(self, host='localhost', port=27017, max_pool_size=10,
        tz_aware=True, _connect=True, logLevel=20, connectionFactory=None,
        **kwargs):
        self.connection = fakeMongoClient

    def disconnect(self):
        self.connection.disconnect()

# single shared connection pool instance
fakeMongoConnectionPool = FakeMongoConnectionPool()
