import sys

from setuptools import setup

__VERSION__ = '0.7.1'


requirements = ['python>=2.7.12', 'pysam==0.13', 'pytest', 'pandas==0.22.0']

setup(name='svSupport',
      version=__VERSION__,
      description='Find allele frequency for structural variants',
      url='https://github.com/nriddiford/svSupport',
      entry_points={
                'console_scripts': [
                    'svSupport=svSupport.svSupport:main'
                ]
            },
      author='Nick Riddiford',
      author_email='nick.riddiford@curie.fr',
      license='MIT',
      packages=['svSupport'],
      install_requires=requirements,
      zip_safe=False)
