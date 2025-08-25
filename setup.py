from setuptools import setup, find_packages

def read_requirements(file):
    with open(file) as f:
        return f.read().splitlines()

setup(
    name="paperqa2-local",
    version="1.0.0",
    packages=find_packages(),
    install_requires=read_requirements("requirements/base.txt"),
    entry_points={
        "console_scripts": [
            "paperqa2-local=paperqa2_local.cli.main:cli",
        ],
    },
    python_requires=">=3.11",
)
