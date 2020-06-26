#!/usr/bin/python3

import os, tempfile
import re
import shutil
import sys
import time
from subprocess import call


EDITOR = os.getenv('EDITOR','vim')
ENTRY_TEMPLATE = """%(pkg_name)s (%(pkg_version)s) %(pkg_distrib)s; %(pkg_urgency)s

  * 

 -- %(debfullname)s <%(debemail)s>  %(debian_formatted_date)s

"""


def read_changelog():
    if os.path.exists('debian/changelog'):
        with open('debian/changelog') as f:
            changelog_content = f.read()
    else:
        print(
            f'You must run {sys.argv[0].split("/")[-1]} in a source package'
            ' containing debian/changelog',
            file=sys.stderr
        )
        sys.exit(1)

    return changelog_content


def retrieve_info(changelog_content):
    first_line = changelog_content[:changelog_content.index('\n')]
    pattern = re.compile(
        r'^(?P<pkg_name>.*) \((?P<pkg_version>.*)\)'
        r' (?P<pkg_distrib>.*); (?P<pkg_urgency>.*)$'
    )
    m = pattern.match(first_line)
    info = m.groupdict()

    return info


def inflate_info(info):
    info['debfullname'] = os.getenv('DEBFULLNAME', '')
    info['debemail'] = os.getenv('DEBEMAIL', '')

    if not info['debfullname']:
        print('DEBFULLNAME env is empty', file=sys.stderr)
        sys.exit(1)

    if not info['debemail']:
        print('DEBEMAIL env is empty', file=sys.stderr)
        sys.exit(1)

    # date format example: Fri, 13 Jul 2012 15:05:04 +0300
    info['debian_formatted_date'] = time.strftime(
        '%a, %d %b %Y %H:%M:%S %z',
        time.localtime()
    )


def increment_version(info):
    # https://www.debian.org/doc/debian-policy/ch-controlfields.html#s-f-version
    version_pattern = re.compile(
        r'^(?P<epoch>\d+:)?(?P<upstream_version>[^-]+)(?P<debian_revision>-.*)?$'
    )
    m = version_pattern.match(info['pkg_version'])
    parts = m.groupdict()

    parts['epoch'] = parts['epoch'] or ''
    parts['debian_revision'] = parts['debian_revision'] or ''

    nums = parts['upstream_version'].split('.')
    if (all(num.isnumeric() for num in nums)):
        nums = list(map(int, nums))

        i = len(nums) - 1

        while True:
            nums[i] += 1

            if i == 0 or nums[i] < 10:
                break

            nums[i] = 0
            i -= 1

    parts['upstream_version'] = '.'.join(map(str, nums))

    new_version = '%(epoch)s%(upstream_version)s%(debian_revision)s' % parts
    info['pkg_version'] = new_version


def write_to_changelog(changelog_content, info):
    new_entry = (ENTRY_TEMPLATE % info) + changelog_content

    with tempfile.NamedTemporaryFile(prefix='changelog.') as f:
        f.write(new_entry.encode())
        f.flush()

        mtime_before = os.path.getmtime(f.name)

        # Spawn Editor
        call([EDITOR, f.name])

        mtime_after = os.path.getmtime(f.name)

        if mtime_before != mtime_after:
            # Copy new file
            shutil.copyfile(f.name, 'debian/changelog')


def main():
    changelog_content = read_changelog()
    info = retrieve_info(changelog_content)

    inflate_info(info)
    increment_version(info)

    write_to_changelog(changelog_content, info)


if __name__ == '__main__':
    main()
