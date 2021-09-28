#!/usr/bin/env python

from setuptools import setup, find_packages


setup(
    name='placebo',
    version='0.10.0',
    description='Make boto3 calls that look real but have no effect',
    long_description=open('README.md').read(),
    long_description_content_type='text/markdown',
    author='Mitch Garnaat',
    author_email='mitch@garnaat.com',
    url='https://github.com/garnaat/placebo',
    packages=find_packages(exclude=['tests*']),
    package_dir={'placebo': 'placebo'},
    license="Apache License 2.0",
    classifiers=[
        'Development Status :: 3 - Alpha',
        'Intended Audience :: Developers',
        'Intended Audience :: System Administrators',
        'Natural Language :: English',
        'License :: OSI Approved :: Apache Software License',
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.6',
        'Programming Language :: Python :: 3.7',
        'Programming Language :: Python :: 3.8',
        'Programming Language :: Python :: 3.9'
    ],
)
