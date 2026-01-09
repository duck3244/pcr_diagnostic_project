"""
PCR Diagnostic Project Setup
"""

from setuptools import setup, find_packages
import os

# Read requirements
def read_requirements():
    req_path = os.path.join(os.path.dirname(__file__), 'requirements.txt')
    with open(req_path, 'r') as f:
        return [line.strip() for line in f if line.strip() and not line.startswith('#')]

setup(
    name='pcr_diagnostic',
    version='1.0.0',
    description='PCR Diagnostic Data Analysis System',
    author='PCR Diagnostic Project',
    python_requires='>=3.8',
    
    # Packages
    packages=find_packages(),
    package_dir={'': '.'},
    
    # Dependencies
    install_requires=read_requirements(),
    
    # Entry points
    entry_points={
        'console_scripts': [
            'pcr-analyze=examples.basic_usage:main',
        ],
    },
    
    # Include package data
    include_package_data=True,
    package_data={
        'data': ['*.csv'],
    },
    
    # Classifiers
    classifiers=[
        'Development Status :: 4 - Beta',
        'Intended Audience :: Science/Research',
        'Topic :: Scientific/Engineering :: Bio-Informatics',
        'Programming Language :: Python :: 3.8',
        'Programming Language :: Python :: 3.9',
        'Programming Language :: Python :: 3.10',
        'Programming Language :: Python :: 3.11',
    ],
)
