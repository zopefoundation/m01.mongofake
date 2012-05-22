##############################################################################
#
# Copyright (c) 2008 Projekt01 GmbH and Contributors.
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

import os
from setuptools import setup, find_packages


def read(*rnames):
    return open(os.path.join(os.path.dirname(__file__), *rnames)).read()

setup(
    name='m01.mongofake',
    version='0.1.0',
    author='Zope Foundation and Contributors',
    author_email='zope-dev@zope.org',
    description="Fake MongoDB implementation",
    long_description=(
        read('README.txt')
        + '\n\n' +
        read('CHANGES.txt')
        ),
    license="ZPL 2.1",
    keywords="mongoDB mongo fake",
    classifiers=[
        'Development Status :: 4 - Beta',
        'Environment :: Web Environment',
        'Intended Audience :: Developers',
        'License :: OSI Approved :: Zope Public License',
        'Programming Language :: Python',
        'Natural Language :: English',
        'Operating System :: OS Independent',
        'Topic :: Internet :: WWW/HTTP'],
    url='http://pypi.python.org/pypi/m01.mongofake',
    packages=find_packages('src'),
    include_package_data=True,
    package_dir={'': 'src'},
    extras_require=dict(
        test=[
            'zope.testing',
        ]),
    install_requires=[
        'setuptools',
        'pymongo',
        ],
    zip_safe=False,
    )
