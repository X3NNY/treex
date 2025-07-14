from setuptools import setup, find_packages

import treex

version = treex.__version__

setup(
    name='treex',
    version=version,
    description='A Python parser for LaTeX documents',
    author='X3NNY',
    author_email='xennyxd1@gmail.com',
    long_description=open("README.md").read(),
    url="https://github.com/X3NNY/treex",
    packages=find_packages('.'),
    install_requires=[],
    classifiers=[
        'Programming Language :: Python :: 3',
        
        'Intended Audience :: Developers',
        'Intended Audience :: Science/Research',
        'Intended Audience :: Education',
        
        'License :: OSI Approved :: MIT License',
        
        'Operating System :: OS Independent',
        
        'Topic :: Software Development :: Libraries :: Python Modules',
        'Topic :: Text Processing :: Markup :: LaTeX',
        'Topic :: Scientific/Engineering :: Mathematics',
        'Topic :: Utilities',
    ],
    python_requires='>=3.7',
)