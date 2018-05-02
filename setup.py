import sys
from setuptools import setup, find_packages

install_requires = [
    'pygments',
    'prompt_toolkit>=0.53',
    'keystoneauth1',
    'requests!=2.12.2,!=2.13.0,>=2.10.0',
    'gevent',
    'datrie'
]

test_requires = []

if sys.version_info[0] == 2:
    install_requires.append('pathlib')
    test_requires.append('mock')


setup(
    name='contrail-api-cli',
    version='0.2.1',
    description="Simple CLI program to browse Contrail API server",
    long_description=open('README.md').read(),
    author="Jean-Philippe Braun",
    author_email="eon@patapon.info",
    maintainer="Jean-Philippe Braun",
    maintainer_email="eon@patapon.info",
    url="http://www.github.com/eonpatapon/contrail-api-cli",
    packages=find_packages(),
    package_data={'contrail_api_cli': ['schemas/*/*']},
    install_requires=install_requires,
    scripts=[],
    license="MIT",
    entry_points={
        'console_scripts': [
            'contrail-api-cli = contrail_api_cli.main:main'
        ],
        'keystoneauth1.plugin': [
            'http = contrail_api_cli.auth:HTTPAuthLoader'
        ],
        'contrail_api_cli.command': [
            'ls = contrail_api_cli.commands.ls:Ls',
            'cat = contrail_api_cli.commands.cat:Cat',
            'du = contrail_api_cli.commands.du:Du',
            'rm = contrail_api_cli.commands.rm:Rm',
            'edit = contrail_api_cli.commands.edit:Edit',
            'shell = contrail_api_cli.commands.shell:Shell',
            'tree = contrail_api_cli.commands.tree:Tree',
            'python = contrail_api_cli.commands.python:Python',
            'schema = contrail_api_cli.commands.schema:Schema',
            'relative = contrail_api_cli.commands.relative:Relative',
            'ln = contrail_api_cli.commands.ln:Ln',
            'exec = contrail_api_cli.commands.exec:Exec',
            'kv = contrail_api_cli.commands.kv:Kv',
            'man = contrail_api_cli.commands.man:Man',
        ],
        'contrail_api_cli.shell_command': [
            'cd = contrail_api_cli.commands.shell:Cd',
            'exit = contrail_api_cli.commands.shell:Exit',
            'help = contrail_api_cli.commands.shell:Help',
        ],
        'contrail_api_cli.completer': [
            'resources = contrail_api_cli.resource:ResourceCache',
            'collections = contrail_api_cli.resource:ResourceCache',
            'commands = contrail_api_cli.manager:CommandManager',
        ]
    },
    classifiers=[
        'Development Status :: 5 - Production/Stable',
        'Intended Audience :: Developers',
        'Topic :: Software Development :: User Interfaces',
        'License :: OSI Approved :: MIT License',
        'Programming Language :: Python :: 2.7',
        'Programming Language :: Python :: 3.4'
    ],
    keywords='contrail api cli',
    tests_require=test_requires,
    test_suite="contrail_api_cli.tests"
)
