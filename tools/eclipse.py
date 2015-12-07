#!/usr/bin/env python
# Copyright (C) 2013 The Android Open Source Project
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
#
# TODO(sop): Remove hack after Buck supports Eclipse

from __future__ import print_function
from optparse import OptionParser
from os import path
from subprocess import Popen, PIPE, CalledProcessError, check_call
from xml.dom import minidom
import re
import sys

MAIN = ['//:classpath']
JRE = '/'.join([
  'org.eclipse.jdt.launching.JRE_CONTAINER',
  'org.eclipse.jdt.internal.debug.ui.launcher.StandardVMType',
  'JavaSE-1.7',
])

ROOT = path.abspath(__file__)
while not path.exists(path.join(ROOT, '.buckconfig')):
  ROOT = path.dirname(ROOT)

opts = OptionParser()
opts.add_option('--src', action='store_true')
opts.add_option('-n', '--name')
args, _ = opts.parse_args()

def _query_classpath(targets):
  deps = []
  p = Popen(['buck', 'audit', 'classpath'] + targets, stdout=PIPE)
  for line in p.stdout:
    deps.append(line.strip())
  s = p.wait()
  if s != 0:
    exit(s)
  return deps


def gen_project(name, root=ROOT):
  p = path.join(root, '.project')
  with open(p, 'w') as fd:
    print("""\
<?xml version="1.0" encoding="UTF-8"?>
<projectDescription>
  <name>""" + name + """</name>
  <buildSpec>
    <buildCommand>
      <name>org.eclipse.jdt.core.javabuilder</name>
    </buildCommand>
  </buildSpec>
  <natures>
    <nature>org.eclipse.jdt.core.javanature</nature>
  </natures>
</projectDescription>\
""", file=fd)

def gen_classpath():
  def make_classpath():
    impl = minidom.getDOMImplementation()
    return impl.createDocument(None, 'classpath', None)

  def classpathentry(kind, path, src=None, out=None):
    e = doc.createElement('classpathentry')
    e.setAttribute('kind', kind)
    e.setAttribute('path', path)
    if src:
      e.setAttribute('sourcepath', src)
    if out:
      e.setAttribute('output', out)
    doc.documentElement.appendChild(e)

  doc = make_classpath()
  src = set()
  lib = set()

  java_library = re.compile(r'[^/]+/gen/(.*)/lib__[^/]+__output/[^/]+[.]jar$')
  for p in _query_classpath(MAIN):
    m = java_library.match(p)
    if m:
      src.add(m.group(1))
    else:
      lib.add(p)

  for s in sorted(src):
    out = None

    if s.startswith('lib/'):
      out = 'eclipse-out/lib'
    elif s.startswith('plugins/'):
      out = 'eclipse-out/' + s

    p = path.join(s, 'java')
    if path.exists(p):
      classpathentry('src', p, out=out)
      continue

    for env in ['main', 'test']:
      o = None
      if out:
        o = out + '/' + env
      elif env == 'test':
        o = 'eclipse-out/test'

      for srctype in ['java', 'resources']:
        p = path.join(s, 'src', env, srctype)
        if path.exists(p):
          classpathentry('src', p, out=o)

  for libs in [lib]:
    for j in sorted(libs):
      s = None
      if j.endswith('.jar'):
        s = j[:-4] + '_src.jar'
        if not path.exists(s):
          s = None
      classpathentry('lib', j, s)

  classpathentry('con', JRE)
  classpathentry('output', 'eclipse-out/classes')

  p = path.join(ROOT, '.classpath')
  with open(p, 'w') as fd:
    doc.writexml(fd, addindent='\t', newl='\n', encoding='UTF-8')

try:
  if args.src:
    try:
      check_call([path.join(ROOT, 'bucklets/tools', 'download_all.py'), '--src'])
    except CalledProcessError as err:
      exit(1)

  name = args.name if args.name else path.basename(ROOT)
  gen_project(name)
  gen_classpath()

  try:
    targets = ['//bucklets/tools:buck'] + MAIN
    check_call(['buck', 'build', '--deep'] + targets)
  except CalledProcessError as err:
    exit(1)
except KeyboardInterrupt:
  print('Interrupted by user', file=sys.stderr)
  exit(1)
