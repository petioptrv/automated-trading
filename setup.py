from glob import glob
from pathlib import Path

from setuptools import setup, find_packages
import versioneer

PACKAGE_PATH = Path(__file__).parent
README = (PACKAGE_PATH / "README.md").read_text()
LICENSE = (PACKAGE_PATH / "LICENSE.txt").read_text()

setup(
    name="algotradepy",
    version=versioneer.get_version(),
    cmdclass=versioneer.get_cmdclass(),
    description="Python Auto-Trading Framework",
    # long_description=README,
    # long_description_content_type="text/markdown",
    author="Petio Petrov",
    author_email="petioptrv@icloud.com",
    url="https://github.com/petioptrv/automated-trading",
    license=LICENSE,
    packages=find_packages(),
    scripts=glob(str(PACKAGE_PATH / "tools" / "*.py")),
    python_requires=">=3.7",  # requires setuptools>=24.2.0, pip>=9.0.0
    install_requires=[
        "numpy >=1, <2",
        "pandas >=1, <2",
        "yfinance <1",
        "pandas_datareader >=0.4.0, <1",
        "requests >=2, <3",
        "pandas_market_calendars >=1, <2",
    ],
    extras_require={
        "ibapi": ["ib_insync >=0.9, <1", "ibapi"],
        "polygon": ["websocket-client==0.57.0"],
        "dev": [
            "pytest",
            "pylint",
            "pre-commit",
            "versioneer",
            "black",
            "flake8",
            "flake8-black",
            "twine",
            "sphinx",
            "sphinx_rtd_theme",
        ],
    },
    classifiers=[
        "Development Status :: 3 - Alpha",
        "Intended Audience :: Developers",
        "Intended Audience :: Science/Research",
        "Intended Audience :: Financial and Insurance Industry",
        "Natural Language :: English",
        "Programming Language :: Python :: 3.7",
        "Programming Language :: Python :: 3.8",
    ],
)
