#!/usr/bin/python3
"""Setup
"""

import os

from setuptools import find_packages
from setuptools.command.test import test as TestCommand
from distutils.core import setup

import unittest

version = "1.0.0"

with open('README.md') as f:
    long_description = f.read()

setup(name='ofxstatement-cd-tmb',
      version=version,
      author="Vincent Luba",
      author_email="vincent@biz-4-africa.com",
      url="https://github.com/BIZ4Africa/ofxstatement-cd-tmb",
      download_url="https://github.com/BIZ4Africa/ofxstatement-cd-tmb/archive/v1.0.zip",
      description=("OFXStatement plugin for TMB (DR Congo)"),
      long_description=open("README.md").read(),
      long_description_content_type='text/markdown',
      license="GPLv3",
      keywords=["ofx", "banking", "statement"],
      classifiers=[
          'Development Status :: 4 - Beta',
          'Programming Language :: Python :: 3',
          'Natural Language :: English',
          'Topic :: Office/Business :: Financial :: Accounting',
          'Topic :: Utilities',
          'Environment :: Console',
          'Operating System :: OS Independent',
          'License :: OSI Approved :: GNU Affero General Public License v3'],
      packages=find_packages('src'),
      package_dir={'': 'src'},
      namespace_packages=["ofxstatement", "ofxstatement.plugins"],
      entry_points={
          'ofxstatement':
          ['tmbcd = ofxstatement.plugins.tmbcd:TmbCdPlugin']
          },
      install_requires=['ofxstatement'],
      extras_require={'test': ["freezegun", "pytest"]},
      include_package_data=True,
      zip_safe=True
      )
