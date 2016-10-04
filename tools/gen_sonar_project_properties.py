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

from __future__ import print_function
from optparse import OptionParser
from os import path, walk
from subprocess import check_output
import re


def guess_maven_group_id(plugin_name, plugin_dir):
  current_dir = None
  for dir_path, dirs, files in walk(path.join(plugin_dir, 'src', 'main', 'java')):
    if len(files) > 0 or len(dirs) > 1 or path.basename(dir_path) == plugin_name:
      break
    current_dir = dir_path

  if current_dir is None:
    return str(hash(plugin_name))

  group_id = []
  while not path.basename(current_dir) == 'java':
    group_id.append(path.basename(current_dir))
    current_dir = path.dirname(current_dir)
  return '.'.join(reversed(group_id))


def get_plugin_version(plugin_dir):
  version = '1.0'
  version_file_path = path.join(plugin_dir, 'VERSION')
  if path.exists(version_file_path):
    try:
      with open(version_file_path, "r") as version_file:
        data = re.sub(r"\s+", '', version_file.read())
    except Exception as err:
      print('error reading plugin version: %s' % err)
    else:
      match = re.search(r"PLUGIN_VERSION='(.*?)'", data)
      if match:
        version = match.group(1)
  elif path.exists(path.join(plugin_dir, '.git')):
    version = check_output(['git', 'describe', '--always', 'HEAD'],
                           cwd=plugin_dir)
  return version


def generate_project_properties(plugin_name, plugin_dir, classes_dir, test_dir,
                                output):
  try:
    with open(output, 'w') as fd:
      print("""\
sonar.projectKey=%s
sonar.projectName=%s
sonar.projectVersion=%s

sonar.language=java
sonar.sources=%s
sonar.tests=%s
sonar.sourceEncoding=UTF-8
sonar.java.source=1.8
sonar.java.binaries=%s

sonar.junit.reportsPath=%s
sonar.core.codeCoveragePlugin=jacoco
sonar.jacoco.reportPath=%s\
""" % (guess_maven_group_id(plugin_name, plugin_dir) + ":" + plugin_name,
       plugin_name,
       get_plugin_version(plugin_dir),
       path.join(plugin_dir, 'src', 'main', 'java'),
       path.join(plugin_dir, 'src', 'test', 'java'),
       classes_dir,
       test_dir,
       path.join(plugin_dir, 'buck-out', 'gen', 'jacoco', 'jacoco.exec')),
            file=fd)
  except Exception as err:
      print('error writing project properties file: %s' % err)


if __name__ == '__main__':
  opts = OptionParser()
  opts.add_option('-n', help='plugin name')
  opts.add_option('-c', help='classes directory')
  opts.add_option('-t', help='test report directory')
  opts.add_option('-o', help='output file', default='sonar-project.properties')
  args, _ = opts.parse_args()

  plugin_dir = path.abspath(__file__)
  for _ in range(0, 3):
    plugin_dir = path.dirname(plugin_dir)
  generate_project_properties(args.n, plugin_dir, path.abspath(args.c),
                              path.abspath(args.t), args.o)
