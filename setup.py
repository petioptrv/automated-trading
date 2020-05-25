import os
from glob import glob
from pathlib import Path
from sys import platform

from setuptools import setup, find_packages

PACKAGE_PATH = Path(os.path.dirname(os.path.realpath(__file__)))

if platform == "linux" or platform == "linux2":  # linux
    ibapi_requires = []
elif platform == "darwin":  # mac
    ibapi_requires = [
        "ibapi @ http://interactivebrokers.github.io/downloads/twsapi_macunix.976.01.zip#subdirectory=IBJts/source/pythonclient",
    ]
elif platform == "win32":  # windows
    pass  # todo: shell script installation
else:
    raise ValueError(f"Unknown platform {platform}.")

setup(
    name="AutoTraderPy",
    version="0.1.0",
    description="Python Auto-Trading Framework",
    author="Petio Petrov",
    author_email="petioptrv@icloud.com",
    packages=find_packages(),
    scripts=glob(str(PACKAGE_PATH / "tools" / "*.py")),
    python_requires=">=3.7",  # requires setuptools>=24.2.0, pip>=9.0.0
    install_requires=[
        "numpy==1.18.2",
        "pandas==1.0.3",
        "yfinance==0.1.54",
        "pandas_datareader>=0.4.0",
        "requests",
        "pandas_market_calendars==1.2",
    ],
    extras_require={
        "ibapi": ibapi_requires,
        "dev": [
            "pytest",
        ]
    },
)

