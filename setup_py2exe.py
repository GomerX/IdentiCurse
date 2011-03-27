#!/usr/bin/env python2
# -*- coding: utf-8 -*-
#
# Copyright (C) 2010-2011 Reality <tinmachin3@gmail.com> and Psychedelic Squid <psquid@psquid.net>
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program. If not, see <http://www.gnu.org/licenses/>.

"""
py2exe build script.
"""

__docformat__ = 'restructuredtext'

from setuptools import setup, find_packages
import py2exe

setup(
    name="identicurse",
    version='0.7',  # 0.7-dev, but py2exe doesn't like the -dev bit.
    description="A simple Identi.ca client with a curses-based UI.",
    long_description=("A simple Identi.ca client with a curses-based UI."),
    author="Psychedelic Squid and Reality",
    author_email='psquid@psquid.net and tinmachin3@gmail.com',
    url="http://identicurse.net/",

    download_url=("http://identicurse.net/release/"),
    license="GPLv3+",

    data_files=[('identicurse',['README', 'conf/config.json'])],
    packages=find_packages('src'),
    package_dir={'': 'src'},
    include_package_data=True,

    entry_points={
        'console_scripts':
            ['identicurse = identicurse:main'],
    },
    
    console=[{
        "script": 'src/identicurse/__init__.py',
        "icon_resources": [(1, 'res/identicurse.ico')],
        "dest_base": 'identicurse',
    }],
    zipfile=None,
    options={
        "py2exe":
            {
                "compressed": 1,
                "optimize": 2,
                "ascii": 1,
                "bundle_files": 1,
                "packages": 'encodings, identicurse',
                "includes": 'identicurse.config, identicurse.textbox, identicurse.helpers, identicurse.statusbar, identicurse.statusnet, identicurse.tabbage, identicurse.tabbar',
                "dll_excludes": 'w9xpopen.exe',  # unneeded, since we don't intend to be runnable on Win9x
            }
    },

    classifiers=[
        'License :: OSI Approved :: GNU General Public License (GPL)',
        'Development Status :: 5 - Production/Stable',
        'Programming Language :: Python',
    ],
)