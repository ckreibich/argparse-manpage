import errno
import unittest
import os
from platform import python_version
import re
import shutil
import subprocess
import sys
from contextlib import contextmanager

from pkg_resources import parse_version
import pytest

sys.path = [os.path.join(os.path.dirname(os.path.realpath(__file__)),'..')]+sys.path

@contextmanager
def pushd(path):
    old_dir = os.getcwd()
    os.chdir(path)
    try:
        yield
    finally:
        os.chdir(old_dir)

@contextmanager
def change_argv(argv):
    old_argv = sys.argv
    sys.argv = argv
    try:
        yield
    finally:
        sys.argv = old_argv


def _rmtree(directory):
    try:
        shutil.rmtree(directory)
    except OSError as err:
        if err.errno != errno.ENOENT:
            raise

def run_pip(args):
    environ = os.environ.copy()
    environ['PYTHONPATH'] = ':'.join(sys.path)
    subprocess.call([sys.executable, '-m', 'pip'] + args + ["--use-feature=in-tree-build", "."],
                    env=environ)


def run_setup_py(args):
    environ = os.environ.copy()
    environ['PYTHONPATH'] = ':'.join(sys.path)
    with change_argv(['setup.py'] + args):
        subprocess.call([sys.executable, 'setup.py'] + args,
                        env=environ)

def skip_if_older_python(min_version):
    def _get_int(version):
        int_v = [int(sv) for sv in version.split(".")]




def run_one_installer(installer, args):
    """
    Run 'pip <args> .' or 'python setup.py <args>'
    """
    if parse_version(python_version()) < parse_version("3.10"):
        if installer == "pip":
            raise pytest.skip("pip install not supported with python %s" %
                              python_version())
    method = run_pip if installer == "pip" else run_setup_py
    method(args)


def file_cmp(file1, file2, filter_string=None):
    with open(file1, 'r') as f1:
        with open(file2, 'r') as f2:
            a1 = f1.readlines()
            a2 = f2.readlines()
            if len(a1) != len(a2):
                # get the pretty diff
                assert a1 == a2

            first = True
            for left, right in zip(a1, a2):
                if first:
                    left  = re.sub('[0-9]{4}\\\\-[0-9]{2}\\\\-[0-9]{2}', '!!DATE!!', left)
                    right = re.sub('[0-9]{4}\\\\-[0-9]{2}\\\\-[0-9]{2}', '!!DATE!!', right)
                    first = False

                if filter_string is not None:
                    left = filter_string(left)
                    right = filter_string(right)

                assert left == right


class TestAllExapmles:
    def test_old_example(self):
        with pushd('examples/old_format'):
            try:
                os.remove('example.1')
            except OSError:
                pass
            run_setup_py(['build_manpage'])
            file_cmp('example.1', 'expected-output.1')


    @pytest.mark.parametrize("installer", ["pip", "setuppy"])
    def test_copr(self, installer):
        with pushd('examples/copr'):
            name = 'copr-cli.1'
            prefix = '/usr'
            idir = os.path.join(os.getcwd(), installer + "_install_dir")
            mandir = os.path.join(idir, "usr/share/man/man1")
            _rmtree(idir)
            run_one_installer(installer, ['install', '--root', idir, '--prefix', prefix])

            def version_version_filter(string):
                return string.replace('[VERSION [VERSION ...]]',
                                      '[VERSION ...]')

            file_cmp(os.path.join(mandir, os.path.basename(name)),
                     'expected-output.1',
                     filter_string=version_version_filter)
            file_cmp(name, 'expected-output.1',
                     filter_string=version_version_filter)


    @pytest.mark.parametrize("installer", ["pip", "setuppy"])
    def test_distgen(self, installer):
        with pushd('examples/raw-description'):
            name = 'man/dg.1'
            prefix = "/usr"
            idir = os.path.join(os.getcwd(), installer + "_install_dir")
            _rmtree(idir)
            mandir = os.path.join(idir, "usr/share/man/man1")
            run_one_installer(installer, ['install', '--root', idir, '--prefix', prefix])
            file_cmp(os.path.join(mandir, os.path.basename(name)), 'expected-output.1')
            file_cmp(name, 'expected-output.1')


    @pytest.mark.parametrize("installer", ["pip", "setuppy"])
    def test_resalloc(self, installer):
        with pushd('examples/resalloc'):
            prefix = "/usr"
            idir = os.path.join(os.getcwd(), installer + "_install_dir")
            _rmtree(idir)
            mandir = os.path.join(idir, "usr/share/man/man1")
            run_one_installer(installer, ['install', '--root', idir, '--prefix', prefix])
            for name in ['man/resalloc.1', 'man/resalloc-maint.1']:
                file_cmp(os.path.join(mandir, os.path.basename(name)),
                         'expected/' + name)
                file_cmp(name, 'expected/' + name)

if __name__ == "__main__":
    unittest.main()