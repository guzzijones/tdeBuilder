from setuptools import setup

setup(
name='tdeBuilder',
version='0.1',
description="Build .tde files from text files",
url="https://github.com/guzzijones/tdeBuilder",
download_url='https://github.com/guzzijones/tdeBuilder/tarball/0.1',
author="Aaron S Jonen",
author_email = 'ajonen@mailcan.com',
license='MIT',
packages=['tdeBuilder'],
keywords=['tableau'],
install_requires=[
'dataextract',
'tableausdk',
'pyodbc'
],
zip_safe=False,
include_package_data=True
)
