#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""PIP setup script for the SDP Processing Controller package."""
# pylint: disable=exec-used

import setuptools
import os

RELEASE_INFO = {}
RELEASE_PATH = os.path.join('src', 'ska_sdp_proccontrol', 'release.py')
exec(open(RELEASE_PATH).read(), RELEASE_INFO)

with open("README.md", "r") as fh:
    LONG_DESCRIPTION = fh.read()

setuptools.setup(
    name=RELEASE_INFO['NAME'],
    version=RELEASE_INFO['VERSION'],
    description="SDP service responsible for the controlling the execution of processing blocks",
    author=RELEASE_INFO['AUTHOR'],
    license=RELEASE_INFO['LICENSE'],
    long_description=LONG_DESCRIPTION,
    long_description_content_type="text/markdown",
    url="https://gitlab.com/ska-telescope/sdp/ska-sdp-proccontrol/",
    package_dir={"": "src"},
    packages=setuptools.find_packages("src"),
    package_data={"ska_sdp_proccontrol": ["schema/*.json"]},
    install_requires=[
        "jsonschema",
        "requests",
        "ska-sdp-config>=0.0.9",
        "ska-logging>=0.3",
    ],
    setup_requires=["pytest-runner"],
    tests_require=["pylint2junit", "pytest", "pytest-cov", "pytest-pylint"],
    zip_safe=False,
    classifiers=[
        "Development Status :: 3 - Alpha",
        "Environment :: Console",
        "Intended Audience :: Science/Research",
        "Topic :: Scientific/Engineering :: Astronomy",
        "Operating System :: POSIX :: Linux",
        "Programming Language :: Python :: 3 :: Only",
        "License :: OSI Approved :: BSD License",
    ],
)
