#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""PIP setup script for the SDP Processing Controller package."""

import setuptools

VERSION = {}
with open("src/ska_sdp_proccontrol/version.py", "r") as fh:
    exec(fh.read(), VERSION)

with open("README.md", "r") as fh:
    LONG_DESCRIPTION = fh.read()

setuptools.setup(
    name="ska-sdp-proccontrol",
    version=VERSION["__version__"],
    description="SDP service responsible for the controlling the execution of processing blocks",
    author="SKA Sim Team",
    license="License :: OSI Approved :: BSD License",
    long_description=LONG_DESCRIPTION,
    long_description_content_type="text/markdown",
    url="https://gitlab.com/ska-telescope/sdp/ska-sdp-proccontrol/",
    package_dir={"": "src"},
    packages=setuptools.find_packages("src"),
    install_requires=[
        "ska-sdp-config",
        "ska-ser-logging",
    ],
    setup_requires=["pytest-runner"],
    tests_require=[
        "pytest",
        "pytest-cov",
    ],
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
