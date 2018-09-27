#!/usr/bin/env python

from setuptools import find_packages, setup

setup(
    name="lpr-placebo",
    version="0.9.0",
    description="Make boto3 calls that look real but have no effect",
    long_description=open("README.md").read(),
    author="Mitch Garnaat, Ilya Pekelny",
    author_email="ilya@launchpadrecruits.com",
    url="https://github.com/launchpadrecruits/lpr-placebo",
    packages=find_packages(exclude=["tests*"]),
    package_dir={"lpr-placebo": "placebo"},
    license="Apache License 2.0",
    classifiers=(
        "Development Status :: 3 - Alpha",
        "Intended Audience :: Developers",
        "Intended Audience :: System Administrators",
        "Natural Language :: English",
        "License :: OSI Approved :: Apache Software License",
        "Programming Language :: Python :: 3.4",
        "Programming Language :: Python :: 3.5",
    ),
)
