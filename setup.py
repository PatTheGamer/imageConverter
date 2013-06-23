'''
Created on Jan 21, 2012

@author: Ryan Moore
'''

from distutils.core import setup
import sys

if sys.platform == 'win32':
    import py2exe
    data_files = [('icons', ['icons\\check_32.png', 'icons\\directory.png', 'icons\\text_directory.png'])]
    setup(windows=['ImageConverter.py'], author='Ryan Moore', data_files=data_files, options={"py2exe": {"unbuffered": True, "optimize": 2}})

else:
    data_files = [('icons', ['icons/check_32.png', 'icons/directory.png', 'icons/text_directory.png'])]
    setup(name='ImageConverter', author='Ryan Moore', data_files=data_files)
