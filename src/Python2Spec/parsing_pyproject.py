from tomlkit import parse
import click
import tarfile
import re
from jinja2 import Template
import email
import os


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


def get_values_from_pkg_info(path_to_tarball):
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
    spec_values = {}
    for key, value in mapping.items():
        if key in content:
            spec_values[value] = content[key]
        else:
            spec_values[value] = None
    return spec_values


@click.command()
@click.argument('path-to-tarball', type=click.Path(exists=True))
def make_spec(path_to_tarball):
    """writes to stdout template updated by information from pkg_info and pyproject.toml"""
    path_to_tarball = os.path.join(os.path.abspath(os.curdir), path_to_tarball)
    # in pyproject.toml must be minimul requirments for building project
    build_requires = get_buildrequires(path_to_tarball)

    try:
        with open(os.path.realpath(__file__).replace(f'{__name__}.py', 'spec_template.jinja2')) as file:
            template = Template(file.read())

            kwargs = get_values_from_pkg_info(path_to_tarball)
            # for key, value in kwargs.items():
            #     click.echo(f"{key}: {value}")
            click.echo(template.render(build_requires=build_requires, **kwargs))

    except OSError as e:
        click.echo(f'Cannot open file: {os.path.abspath(os.curdir)}/{path_to_tarball}')
        click.echo(e.__str__())
        click.echo(os.listdir(f'{os.path.abspath(os.curdir)}/test_tarballs'))


if __name__ == '__main__':
    make_spec()
