from pathlib import Path

import setuptools


def parse_requirements(filename):
    with open(Path(__name__).parent / filename) as f:
        return [l for l in f.readlines() if l[0] not in ["-", "#"]]


setuptools.setup(
    name="dnjs",
    version="0.0.7",
    author="Leon Trolski",
    author_email="ojhrussell@gmail.com",
    description="DOM Notation JS",
    long_description=open("README.md", "r").read(),
    long_description_content_type="text/markdown",
    url="https://github.com/leontrolski/dnjs",
    packages=setuptools.find_packages(),
    include_package_data=True,
    classifiers=[
        "Programming Language :: Python :: 3",
        "Operating System :: OS Independent",
    ],
    install_requires=parse_requirements("requirements.in"),
    extras_require={"dev": parse_requirements("requirements-dev.in")},
    entry_points = {
        'console_scripts': ['dnjs=dnjs.cli:main'],
    }
)
