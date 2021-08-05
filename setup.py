from setuptools import setup, find_packages
import cpp_ast_parser

setup(name='CPP AST Parser',
      version=cpp_ast_parser.__version__,
      description='C++ AST Parser: Parser for c++ code to an AST representation and also from the AST back to code.',
      author='Sander de Bruin',
      author_email='s.d.m.d.bruin@student.tue.nl',
      url='https://github.com/sander102907/cpp_ast_parser',
      packages=find_packages(),
      install_requires=[
          'anytree',
          'clang',
          'llvmlite',
          'numba',
          'numpy',
          'pandas',
          'tqdm',
          'ccsyspath',
      ],
      long_description=open('README.md').read(),
      license='APACHE 2.0'
     )
