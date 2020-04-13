import os
from glob import glob
from pathlib import Path

from setuptools import setup, find_packages

PACKAGE_PATH = Path(os.path.dirname(os.path.realpath(__file__)))

setup(
    name="AutoTraderPy",
    version="0.1.0",
    description="Python Auto-Trading Framework",
    author="Petio Petrov",
    author_email="petioptrv@icloud.com",
    packages=find_packages(),
    scripts=glob(str(PACKAGE_PATH / "tools" / "*.py")),
    install_requires=[
        "numpy==1.18.2",
        "pandas==1.0.3",
        "yfinance==0.1.54",
        "pandas_datareader>=0.4.0",
        "requests",
        "pandas_market_calendars==1.2",
        "pyfakefs==4.0.2",
    ],
    extra_requires={
        "dev": [
            "pytest",
        ]
    }
)

