import pytest
import sys
import os
import Python2Spec
from Python2Spec.parsing_pyproject import *
import click.testing
from _pytest.monkeypatch import monkeypatch
from unittest.mock import patch


def test_get_file_from_tarball():
    print(os.curdir)
    for tarball in os.listdir('test_tarballs'):
        result = get_file_from_tarball('test_tarballs/' + tarball, 'pyproject.toml')
        with open('test_projects/' + tarball.replace('.tar.gz', '') + '/pyproject.toml', 'rb') as f:
            content = f.read()
            assert result == content


def test_get_buildrequires(monkeypatch):
    def mock_get_file_from_tarball(path, file):
        return b'[build-system]\nrequires = ["setuptools", "wheel"]'

    with monkeypatch.context() as m:
        m.setattr('Python2Spec.parsing_pyproject.get_file_from_tarball', mock_get_file_from_tarball)

        assert get_buildrequires('path') == ['setuptools', 'wheel']


def test_get_values_from_pkg_info(monkeypatch):
    def mock_get_file_from_tarball(path, file):
        with open('test_projects/PKG-INFO', 'rb') as f:
            f = f.read()
        return f

    with monkeypatch.context() as m:
        m.setattr('Python2Spec.parsing_pyproject.get_file_from_tarball', mock_get_file_from_tarball)
        expected = {'URL': 'https://pip.pypa.io/', 'pypi_name': 'pip', 'Version': '19.0.3', 'License': 'MIT',
                    'Summary': 'The PyPA recommended tool for installing Python packages.',
                    'Description': "pip",
                    }

        assert get_values_from_pkg_info('path') == expected


def test_make_spec(monkeypatch):
    runner = click.testing.CliRunner()

    def mock_get_buildrequires(*args, **kwargs):
        return '[setuptools, wheel]'

    def mock_get_values_from_pkg_info(*args, **kwargs):
        return {'URL': 'https://pip.pypa.io/', 'pypi_name': 'pip', 'Version': '19.0.3', 'License': 'MIT',
                'Summary': 'The PyPA recommended tool for installing Python packages.',
                'Description': "pip",
                }

    with monkeypatch.context() as m:
        m.setattr('Python2Spec.parsing_pyproject.get_buildrequires', mock_get_buildrequires)
        m.setattr('Python2Spec.parsing_pyproject.get_values_from_pkg_info', mock_get_values_from_pkg_info)
        result = runner.invoke(make_spec, ['path'])
        assert result.exit_code == 2

        with open('./tests/generated_specfile', 'r') as f:
            with patch('Python2Spec.parsing_pyproject.click.echo') as mocked_method:
                result = runner.invoke(make_spec, ['test_tarballs/pip-19.0.3.tar.gz'])
                assert result.exit_code == 0
                expected = f.read()
            # print(result.output)
            # test = result.output
            # for i, line in enumerate(expected):
            #     if (test[i] + '\n') != line:
            #         print(f'{line}:{test[i]}')
        assert mocked_method.call_with(expected)
