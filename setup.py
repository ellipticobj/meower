from setuptools import setup, find_packages # type: ignore
import sys
from meow.config import VERSION

# get the correct platform tag
def get_platform_tag():
    if sys.platform.startswith('linux'):
        import platform
        arch = platform.machine()
        if arch == 'aarch64':
            return 'manylinux2014_aarch64'
        elif arch == 'x86_64':
            return 'manylinux2014_x86_64'
    return None

setup(
    name='meower',
    version=VERSION,
    author='ellipticobj',
    author_email='luna@hackclub.app',
    description='A short description of your package',
    packages=find_packages(),
    classifiers=[
        'Programming Language :: Python :: 3',
        'License :: OSI Approved :: MIT License',
        'Operating System :: OS Independent',
    ],
    python_requires='>=3.12',
    # add platform-specific tags if needed
    options={'bdist_wheel': {'plat_name': get_platform_tag()}} if get_platform_tag() else {}
)