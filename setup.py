from glob import glob
from pathlib import Path

from setuptools import setup, find_packages

PACKAGE_PATH = Path(__file__).parent

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
        "numpy >=1, <2",
        "pandas >=1, <2",
        "yfinance <1",
        "pandas_datareader >=0.4.0, <1",
        "requests >=2, <3",
        "pandas_market_calendars >=1, <2",
    ],
    extras_require={
        "ibapi": ["ibapi >=9, <10"],
        "dev": [
            "pytest",
        ]
    },
)

