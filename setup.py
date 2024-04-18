#!/usr/bin/env python3
import sys
from io import open
import os.path as osp
from setuptools import setup


HERE = osp.abspath(osp.dirname(__file__))
sys.path.insert(0, HERE)
import pibooth_mqtt_counter as plugin  # nopep8 : import shall be done after adding setup to paths


def main():
    setup(
        name=plugin.__name__,
        version=plugin.__version__,
        description=plugin.__doc__,
        author="Poupounet Joyeux",
        url="https://github.com/poupounetjoyeux/pibooth-mqtt-counter",
        license='GPLv3',
        platforms=['unix', 'linux'],
        keywords=[
            'Raspberry Pi',
            'counter',
            'photobooth',
            'pibooth',
            'plugin'
        ],
        py_modules=['pibooth_mqtt_counter'],
        python_requires=">=3.6",
        install_requires=[
            'pibooth>=2.0.0',
            'paho-mqtt>=2.0.0'
        ],
        zip_safe=False,  # Don't install the lib as an .egg zipfile
        entry_points={'pibooth': ["pibooth_mqtt_counter = pibooth_mqtt_counter"]},
    )


if __name__ == '__main__':
    main()