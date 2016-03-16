import sys
from setuptools import setup, find_packages

install_requires = [
    'pygments',
    'prompt_toolkit>=0.53',
    'python-keystoneclient',
    'tabulate'
]

test_requires = []

if sys.version_info[0] == 2:
    install_requires.append('pathlib')
    test_requires.append('mock')


setup(
    name='contrail-api-cli',
    version='0.1b2',
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
        'keystoneclient.auth.plugin': [
            'http = contrail_api_cli.auth:HTTPAuth'
        ],
        'contrail_api_cli.command': [
            'ls = contrail_api_cli.command:Ls',
            'cat = contrail_api_cli.command:Cat',
            'count = contrail_api_cli.command:Count',
            'rm = contrail_api_cli.command:Rm',
            'edit = contrail_api_cli.command:Edit',
            'shell = contrail_api_cli.command:Shell',
            'tree = contrail_api_cli.command:Tree',
            'code = contrail_api_cli.command:Python',
            'schema = contrail_api_cli.commands.schema:Schema',
        ],
        'contrail_api_cli.shell_command': [
            'cd = contrail_api_cli.command:Cd',
            'set = contrail_api_cli.command:Set',
            'exit = contrail_api_cli.command:Exit',
            'help = contrail_api_cli.command:Help',
        ]
    },
    classifiers=[
        'Development Status :: 3 - Alpha',
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
