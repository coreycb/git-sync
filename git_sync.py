#!/usr/bin/python

# Copyright 2016 Canonical Limited.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#  http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

# Authors:
#   Chris MacNaughton <chris.macnaughton@canonical.com>

import logging
import optparse
import os
import subprocess
import sys
import tempfile
import shutil

from glob import fnmatch


def clone(dest, source, branch=None):
    logging.info('Checking out %s to %s.' % (branch, dest))
    cmd = ['git', 'clone', '--quiet', '--depth=1']
    if branch is not None:
        cmd.append("--branch={}".format(branch))
    cmd.append(source)
    cmd.append(dest)
    subprocess.check_call(cmd)
    return dest


def sync(src, dest, rename=None):
    if os.path.exists(dest):
        logging.debug('Removing existing directory: %s' % dest)
        shutil.rmtree(dest)

    allowed = ["charms_ceph"]
    for e in os.listdir(src):
        if e in allowed:
            logging.info('Syncing directory: %s -> %s.' % (e, dest))
            shutil.copytree(os.path.join(src, e), os.path.join(dest, e),
                            ignore=get_filter())
            if rename:
                shutil.move(os.path.join(dest, e), os.path.join(dest, rename))


def get_filter(opts=None):
    opts = opts or []
    if 'inc=*' in opts:
        # do not filter any files, include everything
        return None

    def _filter(dir, ls):
        incs = [opt.split('=').pop() for opt in opts if 'inc=' in opt]
        filtered = []
        for f in ls:
            _f = os.path.join(dir, f)

            if not os.path.isdir(_f) and not _f.endswith('.py') and incs:
                if True not in [fnmatch.fnmatch(_f, inc) for inc in incs]:
                    logging.debug('Not syncing %s, does not match include '
                                  'filters (%s)' % (_f, incs))
                    filtered.append(f)
                else:
                    logging.debug('Including file, which matches include '
                                  'filters (%s): %s' % (incs, _f))
            elif (os.path.isfile(_f) and not _f.endswith('.py')):
                logging.debug('Not syncing file: %s' % f)
                filtered.append(f)
            elif (os.path.isdir(_f) and ('test' in f)):
                logging.debug('Not syncing directory: %s' % f)
                filtered.append(f)
            elif (os.path.isdir(_f) and not
                  os.path.isfile(os.path.join(_f, '__init__.py'))):
                logging.debug('Not syncing directory: %s' % f)
                filtered.append(f)
        return filtered

    return _filter

if __name__ == '__main__':
    parser = optparse.OptionParser()
    parser.add_option('-s', '--source', action='store', dest='source',
                      help='source repository')
    parser.add_option('-D', '--debug', action='store_true', dest='debug',
                      default=False, help='debug')
    parser.add_option('-b', '--branch', action='store', dest='branch',
                      help='git branch')
    parser.add_option('-d', '--destination', action='store', dest='dest_dir',
                      help='sync destination dir')
    parser.add_option('-r', '--rename', action='store', dest='rename',
                      help='rename the cloned repository')

    (opts, args) = parser.parse_args()

    if opts.debug:
        logging.basicConfig(level=logging.DEBUG)
    else:
        logging.basicConfig(level=logging.INFO)

    config = {}
    if opts.branch:
        config['branch'] = opts.branch
    if opts.source:
        config['source'] = opts.source
    if opts.dest_dir:
        config['dest'] = opts.dest_dir
    if opts.rename:
        config['rename'] = opts.rename
    else:
        config['rename'] = None

    if 'source' not in config:
        logging.error('No source repo specified as an option')
        sys.exit(1)

    if 'dest' not in config:
        logging.error('No destination dir. specified as option or config.')
        sys.exit(1)

    if 'branch' not in config:
        config['branch'] = 'master'

    tmpd = tempfile.mkdtemp()

    try:
        checkout = clone(tmpd, config['source'], config['branch'])
        sync(checkout, config['dest'], config['rename'])
    except Exception as e:
        logging.error("Could not sync: %s" % e)
        raise e
    finally:
        logging.debug('Cleaning up %s' % tmpd)
        shutil.rmtree(tmpd)
