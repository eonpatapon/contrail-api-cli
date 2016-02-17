import sys
from setuptools import setup, find_packages

install_requires = [
    'prompt_toolkit==0.54',
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
    include_package_data=True,
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
            'ls = contrail_api_cli.commands:Ls',
            'cat = contrail_api_cli.commands:Cat',
            'count = contrail_api_cli.commands:Count',
            'rm = contrail_api_cli.commands:Rm',
            'edit = contrail_api_cli.commands:Edit',
            'shell = contrail_api_cli.commands:Shell',
            'tree = contrail_api_cli.commands:Tree',
        ],
        'contrail_api_cli.shell_command': [
            'cd = contrail_api_cli.commands:Cd',
            'set = contrail_api_cli.commands:Set',
            'exit = contrail_api_cli.commands:Exit',
            'help = contrail_api_cli.commands:Help',
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
