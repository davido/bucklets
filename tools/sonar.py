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


# This script runs a Sonarqube analysis for a Gerrit plugin and uploads the
# results to the local Sonarqube instance, similar to what `mvn sonar:sonar`
# would do.
#
# It will build the plugin, run the tests, generate sonar-project.properties
# file and then call sonar-runner (sonar-runner must be installed and available
# in the path).
#
# This script must be called from the root folder of a gerrit plugin supporting
# standalone buck build:
#
# ./bucklets/tools/sonar.py
#

from __future__ import print_function
from os import path, makedirs
import re
from shutil import rmtree
from tempfile import mkdtemp
from subprocess import call, check_call, CalledProcessError
from zipfile import ZipFile

from gen_sonar_project_properties import generate_project_properties


def get_plugin_name(buck_file):
  try:
    with open(buck_file, "r") as f:
      data = re.sub(r"\s+", '', f.read())
    return re.search(r"gerrit_plugin\(name='(.*?)'.*\)$", data).group(1)
  except Exception as err:
    exit('Failed to read plugin name from BUCK file: %s' % err)


plugin_dir = path.abspath(__file__)
for _ in range(0, 3):
  plugin_dir = path.dirname(plugin_dir)

plugin_name = get_plugin_name(path.join(plugin_dir, 'BUCK'))

temp_dir = mkdtemp()
try:
  try:
    check_call(['buck', 'build', '//:' + plugin_name])
  except CalledProcessError as err:
    exit(1)

  classes_dir = path.join(temp_dir, 'classes')
  with ZipFile(path.join(plugin_dir, 'buck-out', 'gen', plugin_name + '.jar'),
               "r") as z:
    z.extractall(classes_dir)

  test_report = path.join(temp_dir, 'testReport.xml')
  call(['buck', 'test', '--no-results-cache', '--code-coverage', '--xml',
        test_report])

  junit_test_report_dir = path.join(temp_dir, 'junitTestReport')
  makedirs(junit_test_report_dir)

  try:
    check_call(
      [path.join(path.abspath(path.dirname(__file__)), 'buck_to_junit.py'),
       '-t', test_report, '-o', junit_test_report_dir])
  except CalledProcessError as err:
    exit(1)

  sonar_project_properties = path.join(temp_dir, 'sonar-project.properties')

  generate_project_properties(plugin_name, plugin_dir, classes_dir,
                              junit_test_report_dir, sonar_project_properties)

  try:
    check_call(['sonar-runner',
                '-Dproject.settings=' + sonar_project_properties, ])
  except CalledProcessError as err:
    exit(1)
finally:
  rmtree(path.join(plugin_dir, '.sonar'), ignore_errors=True)
  rmtree(temp_dir, ignore_errors=True)
