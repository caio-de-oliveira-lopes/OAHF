from pathlib import Path

from Cython.Build import cythonize
from setuptools import find_packages, setup

requirements_path = Path("requirements.txt").resolve()

if requirements_path.is_file():
    with open(requirements_path, "r", encoding="utf-8-sig") as fp:
        requirements = fp.read().splitlines()
else:
    print("No requirements.txt found. Skipping.")
    requirements = []

setup(
    name="oahf",
    version="1.0.0",
    author="Caio de Oliveira Lopes",
    author_email="caio.oliveiracvt@gmail.com",
    description="",
    long_description=open("README.md", encoding="utf-8").read(),
    long_description_content_type="text/markdown",
    url="",
    packages=find_packages(),
    include_package_data=True,
    ext_modules=cythonize(
        "oahf/**/*.py",  # or use "oahf/**/*.pyx" if you have renamed files to .pyx
        compiler_directives={
            "language_level": "3",  # Use Python 3 syntax
            "boundscheck": False,  # Disable bounds checking for speed
            "wraparound": False,  # Disable negative index wraparound for speed
        },
    ),
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
    ],
    python_requires=">=3.9",
    install_requires=requirements,
)
