======
README
======

Let's test some mongofake helper methods.

  >>> import re
  >>> import datetime
  >>> import bson.tz_util
  >>> import m01.mongofake
  >>> from m01.mongofake import pprint


RENormalizer
------------

The RENormalizer is able to normalize text and produce comparable output. You
can setup the RENormalizer with a list of input, output expressions. This is
usefull if you dump mongodb data which contains dates or other not so simple 
reproducable data. Such a dump result can get normalized before the unit test
will compare the output. Also see zope.testing.renormalizing for the same
pattern which is useable as a doctest checker.

  >>> normalizer = m01.mongofake.RENormalizer([
  ...    (re.compile('[0-9]*[.][0-9]* seconds'), '... seconds'),
  ...    (re.compile('at 0x[0-9a-f]+'), 'at ...'),
  ...    ])

  >>> text = """
  ... <object object at 0xb7f14438>
  ... completed in 1.234 seconds.
  ... ...
  ... <object object at 0xb7f14450>
  ... completed in 1.234 seconds.
  ... """

  >>> print normalizer(text)
  <BLANKLINE>
  <object object at ...>
  completed in ... seconds.
  ...
  <object object at ...>
  completed in ... seconds.
  <BLANKLINE>

Now let's test some mongodb relevant stuff:

  >>> from bson.dbref import DBRef
  >>> from bson.min_key import MinKey
  >>> from bson.max_key import MaxKey
  >>> from bson.objectid import ObjectId
  >>> from bson.timestamp import Timestamp

  >>> import time
  >>> import calendar
  >>> import struct
  >>> def getObjectId(secs=0):
  ...    """Knows how to generate similar ObjectId based on integer (counter)"""
  ...    time_tuple = time.gmtime(secs)
  ...    ts = calendar.timegm(time_tuple)
  ...    oid = struct.pack(">i", int(ts)) + "\x00" * 8
  ...    return ObjectId(oid)

  >>> oid = getObjectId(42)
  >>> oid
  ObjectId('0000002a0000000000000000')

  >>> data = {'oid': oid,
  ...         'dbref': DBRef("foo", 5, "db"),
  ...         'date': datetime.datetime(2011, 5, 7, 1, 12),
  ...         'utc': datetime.datetime(2011, 5, 7, 1, 12, tzinfo=bson.tz_util.utc),
  ...         'min': MinKey(),
  ...         'max': MaxKey(),
  ...         'timestamp': Timestamp(4, 13),
  ...         're': re.compile("a*b", re.IGNORECASE),
  ...         'string': 'string',
  ...         'unicode': u'unicode',
  ...         'int': 42}

Now let's pretty print the data:

  >>> pprint(data)
  {'date': datetime.datetime(2011, 5, 7, 1, 12),
   'dbref': DBRef('foo', 5, 'db'),
   'int': 42,
   'max': MaxKey(),
   'min': MinKey(),
   'oid': ObjectId('0000002a0000000000000000'),
   're': <_sre.SRE_Pattern object at ...>,
   'string': 'string',
   'timestamp': Timestamp(4, 13),
   'unicode': u'unicode',
   'utc': datetime.datetime(2011, 5, 7, 1, 12, tzinfo=<bson.tz_util.FixedOffset object at ...>)}


reNormalizer
------------

As you can see our predefined reNormalizer will convert the values using our
given patterns: 

  >>> import m01.mongofake
  >>> print m01.mongofake.reNormalizer(data)
  {'date': datetime.datetime(...),
   'dbref': DBRef('foo', 5, 'db'),
   'int': 42,
   'max': MaxKey(),
   'min': MinKey(),
   'oid': ObjectId('...'),
   're': <_sre.SRE_Pattern object at ...>,
   'string': 'string',
   'timestamp': Timestamp('...'),
   'unicode': u'unicode',
   'utc': datetime(..., tzinfo=<bson.tz_util.FixedOffset ...>)}


pprint
------

  >>> m01.mongofake.reNormalizer.pprint(data)
  {'date': datetime.datetime(...),
   'dbref': DBRef('foo', 5, 'db'),
   'int': 42,
   'max': MaxKey(),
   'min': MinKey(),
   'oid': ObjectId('...'),
   're': <_sre.SRE_Pattern object at ...>,
   'string': 'string',
   'timestamp': Timestamp('...'),
   'unicode': u'unicode',
   'utc': datetime(..., tzinfo=<bson.tz_util.FixedOffset ...>)}


dictify
-------

  >>> import bson.son
  >>> son = bson.son.SON(data)
  >>> type(son)
  <class 'bson.son.SON'>

  >>> res = m01.mongofake.dictify(son)
  >>> type(res)
  <type 'dict'>

  >>> m01.mongofake.pprint(res)
  {'date': datetime.datetime(2011, 5, 7, 1, 12),
   'dbref': DBRef('foo', 5, 'db'),
   'int': 42,
   'max': MaxKey(),
   'min': MinKey(),
   'oid': ObjectId('0000002a0000000000000000'),
   're': <_sre.SRE_Pattern object at ...>,
   'string': 'string',
   'timestamp': Timestamp(4, 13),
   'unicode': u'unicode',
   'utc': datetime.datetime(2011, 5, 7, 1, 12, tzinfo=<bson.tz_util.FixedOffset object at ...>)}
