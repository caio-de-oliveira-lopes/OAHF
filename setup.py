from pathlib import Path

from setuptools import find_packages, setup

requirements_path = Path("requirements.txt").resolve()

if requirements_path.is_file():
    with open(
        requirements_path,
        errors="ignore",
        encoding="utf-8-sig",
        buffering=1,
        mode="r",
    ) as fp:
        requirements = fp.read().splitlines()
        fp.close()
else:
    print("No requirements.txt found. Skipping.")
    # Empty requirements list to avoid error
    requirements = []

setup(
    name="oahf",
    version="1.0.0",
    author="Caio de Oliveira Lopes",
    author_email="caio.oliveiracvt@gmail.com",
    description="",
    long_description=open("README.md").read(),
    long_description_content_type="text/markdown",
    url="",
    packages=find_packages(),
    # data_files=[("Resources", ["pelloptml/Resources/LogMessages.resx"])],
    include_package_data=True,
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
    ],
    python_requires=">=3.9",
    install_requires=requirements,
)
