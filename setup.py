from setuptools import setup, find_packages

setup(
    name="competitor-analysis",
    version="0.1.0",
    description="Competitive Intelligence Platform - Multi-agent competitor research and analysis",
    author="shinny77",
    python_requires=">=3.11",
    packages=find_packages(),
    install_requires=[
        "anthropic>=0.39.0",
        "openai>=1.50.0",
        "google-generativeai>=0.8.0",
        "click>=8.1.0",
        "python-dotenv>=1.0.0",
        "requests>=2.31.0",
        "beautifulsoup4>=4.12.0",
        "python-docx>=1.1.0",
        "pydantic>=2.5.0",
    ],
    entry_points={
        "console_scripts": [
            "competitor-analysis=src.cli:cli",
        ],
    },
)
