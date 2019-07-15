from tomlkit import parse
import click
import tarfile
import re
from jinja2 import Template
import email
import os
from datetime import date
import locale


def get_file_from_tarball(path_to_tarball, file):
    """returns content of file"""
    with tarfile.open(os.path.join(path_to_tarball), f'r:gz') as tar:
        # finding prefix to pyproject.toml

        prefix = ''
        pattern = f"(.*){file}"
        for filepath in tar.getnames():
            if re.match(pattern, filepath):
                pattern = f"(.*){file}"
                prefix = re.match(pattern, filepath)[1]
                break
        if not prefix:
            raise FileNotFoundError('File is not in tarball')
        buffer = tar.extractfile(f"{prefix}{file}")
        content = buffer.read()
    return content


def get_buildrequires(path_to_tarball):
    """ returns buildrequires from tarball"""
    buffer = get_file_from_tarball(path_to_tarball, 'pyproject.toml')
    buffer = parse(buffer)
    return buffer['build-system']['requires']


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


@click.command()
@click.option('--email', type=str)
@click.option('--name', type=str)
@click.argument('path-to-tarball', type=click.Path(exists=True))
def make_spec(path_to_tarball, name, email):
    name = name if name else 'name'
    email = email if email else 'email'

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
