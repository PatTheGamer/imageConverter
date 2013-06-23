'''
Created on Jan 21, 2012

@author: Ryan Moore
'''

from distutils.core import setup

import py2exe

import os

MyData_files=[]

MyData_files = [('icons', ['icons/check_32.png','icons/directory.png','icons/text_directory.png'])]
print str(MyData_files)

setup(windows=['ImageConverter.py'], data_files = MyData_files, options={"py2exe":{"unbuffered": True, "optimize": 2}})
