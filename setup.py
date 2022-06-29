from setuptools import setup, find_packages

with open('./requirements.txt') as f:
    requirements = f.read().split('\n')
    
setup(
    name='mps_database',
    version='3.0.0',
    author='Jeremy Mock',
    author_email='jmock@slac.stanford.edu',
    packages=find_packages(include=['mps_database'], exclude=[]),
    url='https://github.com/slaclab/mps_database',
    license='MIT',
    description='Various tools and scripts for the mps database.',
    long_description=open('README.md').read(),
    install_requires=requirements
)
