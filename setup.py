from setuptools import setup, find_packages

install_requires = [
    'prompt_toolkit',
    'requests'
]

test_requires = [
    'mock'
]

setup(
    name='contrail-api-cli',
    version='0.1a1',
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
            'contrail-api-cli = contrail_api_cli.prompt:main',
        ],
    },
    classifiers=[
        'Development Status :: 3 - Alpha',
        'Intended Audience :: Developers',
        'Topic :: Software Development :: User Interfaces',
        'License :: OSI Approved :: MIT License',
        'Programming Language :: Python :: 2.7',
        'Programming Language :: Python :: 3.4',
        'Programming Language :: Python :: 3.5'
    ],
    keywords='contrail api cli',
    tests_require=test_requires,
    test_suite="contrail_api_cli.tests"
)
