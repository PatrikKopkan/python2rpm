from tomlkit import parse
import click
import tarfile
import re
from jinja2 import Template, Environment, PackageLoader, select_autoescape
import email


def get_file_from_tarball(path_to_tarball, file):
    "returns content of file"
    tar = tarfile.open(path_to_tarball, f'r:gz')
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
    return buffer.read()


def get_buildrequires(path_to_tarball):
    """ expects path to tar.gz tarballs"""
    buffer = get_file_from_tarball(path_to_tarball, 'pyproject.toml')
    buffer = parse(buffer)
    return buffer['build-system']['requires']


def get_values_from_pkg_info(path_to_tarball):
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

    # in pyproject.toml must be minimul requirments for building project
    build_requires = get_buildrequires(path_to_tarball)

    with open('./Python2Spec/spec_template.jinja2') as file:
        template = Template(file.read())

    kwargs = get_values_from_pkg_info(path_to_tarball)
    # for key, value in kwargs.items():
    #     click.echo(f"{key}: {value}")
    click.echo(template.render(build_requires=build_requires, **kwargs))


if __name__ == '__main__':
    make_spec()
