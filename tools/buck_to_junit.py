#!/usr/bin/env python
# Copyright (C) 2015 The Android Open Source Project
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
# http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

from optparse import OptionParser
from os import path, chdir
from os.path import abspath
from shutil import rmtree
from subprocess import check_call, CalledProcessError
from tempfile import mkdtemp

opts = OptionParser()
opts.add_option('-t', help='test report to convert')
opts.add_option('-o', help='output directory')
args, _ = opts.parse_args()
temp_dir = mkdtemp()
try:
  try:
    check_call(
      ['mvn', 'org.apache.maven.plugins:maven-dependency-plugin:copy',
       '-Dmdep.stripVersion=true', '-Dartifact=net.sf.saxon:Saxon-HE:9.6.0-6',
       '-DoutputDirectory=' + temp_dir])
  except OSError as err:
    print('could not invoke mvn: %s\nis mvn installed?' % err)
    exit(1)
  except CalledProcessError as err:
    print('error using mvn: %s' % err)
    exit(1)

  buck_report = abspath(args.t)
  buck_to_junit_xsl = abspath(
    path.join(path.abspath(path.dirname(__file__)), 'buckToJUnit.xsl'))

  chdir(args.o)
  try:
    check_call(
      ['java', '-jar', path.join(temp_dir, 'Saxon-HE.jar'), '-s:' + buck_report,
       '-xsl:' + buck_to_junit_xsl])
  except CalledProcessError as err:
    print('error converting to junit: %s' % err)
    exit(1)
finally:
  rmtree(temp_dir, ignore_errors=True)
