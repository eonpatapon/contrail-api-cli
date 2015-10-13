from setuptools import setup, find_packages

install_requires = [
    'prompt_toolkit',
    'requests',
    'nose',
    'mock'
]

setup(
    name='Contrail API Cli',
    version='0.1',
    description="Simple CLI program to browse Contrail API server",
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
            'contrail-api-cli = contrail_api_cli.prompt:main',
        ],
    }
)
