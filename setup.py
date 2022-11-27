#!/usr/bin/env python3

from distutils.core import setup

setup(name='zwave-js-helper',
        version='1.0',
        description='Z-Wave JS Helper to mass-set values.',
        author='Omen Wild',
        author_email='omen@mandarb.com',
        url='https://github.com/OmenWild/zwave-js-helper',
        scripts=['zwave-js-helper.py'],
        install_requires=[
            'websocket-client>=1.4.2',
            'pyxdg>=0.27',
            'pyyaml>=6.0',
        ]
     )
