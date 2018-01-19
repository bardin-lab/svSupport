import sys

from setuptools import setup

__VERSION__ = '0.1'

requirements = ['pysam', 'pytest']

setup(name='svSupport',
      version=__VERSION__,
      description='Find allele frequency for structural variants',
      url='https://github.com/nriddiford/svSupport',
      author='Nick Riddiford',
      author_email='nick.riddiford@curie.fr',
      license='MIT',
      packages=['svSupport'],
      install_requires=requirements,
      zip_safe=False)