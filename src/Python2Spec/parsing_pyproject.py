from tomlkit import parse
import click
import tarfile
import re
from jinja2 import Template
import email
import os
from datetime import date
import locale
import subprocess
from typing import Union

#
# def get_toplevel_dir(path_to_tarball: str, file: str) -> Union[None, str]:
#     """ gets name of compressed directory"""
#     with tarfile.open(os.path.join(path_to_tarball), f'r:gz') as tar:
#         directory = set()
#         click.echo('toml' in tar.getnames())
#         for filepath in tar.getnames():
#             new_directory = re.match(r'^/(.+)/', filepath)
#             if new_directory:
#                 directory.add(new_directory[1])
#     if len(directory) == 1:
#         return new_directory
#     else:
#         return directory

def get_toplevel_dir(path_to_tarball):
    """ gets name of compressed directory"""
    with tarfile.open(os.path.join(path_to_tarball), f'r:gz') as tar:
        file = tar.getnames()[1]
        return re.match("(.*)/", file)[1]

def find_file_from_tarball(path_to_tarball, file):
    """returns content of file"""
    with tarfile.open(os.path.join(path_to_tarball), f'r:gz') as tar:
        # finding prefix to file
        files = []
        prefix = ''
        pattern = f"(.*){file}"
        for filepath in tar.getnames():
            if re.match(pattern, filepath):
                pattern = f"(.*){file}"
                files.append(re.match(pattern, filepath)[0])
    return files

# zjistit jak funguje context manager kdyz se v nem budu chtit vratit z funkce


def get_file_from_tarball(path_to_tarball, file) -> bytes:
    """get content of file in b"""
    with tarfile.open(os.path.join(path_to_tarball), f'r:gz') as tar:
        try:
            topdir = get_toplevel_dir(path_to_tarball)
            #click.echo(f"topdir: {topdir}")
            if topdir:
                buffer = tar.extractfile(os.path.join(topdir, file))
                content = buffer.read()
                return content
        except Exception as e:
            click.echo(e)


def get_buildrequires(path_to_tarball):
    """ returns buildrequires from tarball"""
    try:
        buffer = get_file_from_tarball(path_to_tarball, 'pyproject.toml')
        if buffer is not None:
            buffer = parse(buffer)
            return buffer['build-system']['requires']
    except FileNotFoundError:
        return []
    return []


def get_items_from_pkg_info(path_to_tarball):
    """
    parses pkg_info file(should be in every source distribution).
    and returns dict[]
    """
    mapping = {
        'Home-page': 'URL',
        'Name': 'pypi_name',
        'Version': 'Version',
        'License': 'License',
        'Summary': 'Summary',
        'Description': 'Description',
    }

    content = get_file_from_tarball(path_to_tarball, 'PKG-INFO')
    content = email.message_from_bytes(content)
    spec_items = {}
    for key, value in mapping.items():
        if key in content:
            spec_items[value] = content[key]
        else:
            spec_items[value] = None
    return spec_items


def git_config(parametr):
    result = subprocess.run(['git', 'config', '--get', f'user.{parametr}'], capture_output=True)
    if result.stdout:
        return result.stdout.decode().strip()
    else:
        return parametr

# todo: look at Download-URL parametr in PKG-INFO
@click.command()
@click.option('--email', type=str)
@click.option('--name', type=str)
@click.argument('path-to-tarball', type=click.Path(exists=True))
def make_spec(path_to_tarball, name, email):
    name = name if name else git_config('name')
    email = email if email else git_config('email')

    """writes to stdout template updated by information from pkg_info and pyproject.toml"""
    path_to_tarball = os.path.join(os.path.abspath(os.curdir), path_to_tarball)
    # in pyproject.toml must be minimul requirments for building project
    build_requires = get_buildrequires(path_to_tarball)
    try:
        with open(os.path.realpath(__file__).replace(f'{__name__}.py', 'spec_template.jinja2')) as file:
            template = Template(file.read())
            spec_items = get_items_from_pkg_info(path_to_tarball)

            locale.setlocale(locale.LC_ALL, 'en_US')
            today = (date.today()).strftime('%a %b %d %Y')

            click.echo(template.render(build_requires=build_requires, **spec_items, name=name, email=email, date=today))

    except OSError as e:
        click.echo(f'Cannot open file: {os.path.abspath(os.curdir)}/{path_to_tarball}')
        click.echo(e)


if __name__ == '__main__':
    make_spec()


#todo: otestovat python3 ./src/Python2Spec/ ~/Documents/rpm/python-distlib/distlib-0.2.9.post0.tar.gz
