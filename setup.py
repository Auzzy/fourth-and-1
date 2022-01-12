from setuptools import find_packages, setup

setup(
    name='fourthand1core',
    version="0.1",
    author="Austin Noto-Moniz",
    author_email="mathfreak65@gmail.com",
    packages=find_packages(),
    package_data={"fourthand1": ["data/*", "data/cards/*", "data/cards/offense/*", "data/cards/defense/*"]},
    python_requires=">=3.6"
)

