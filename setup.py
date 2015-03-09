from distutils.core import setup

setup(name='cli2web',
      version='0.1',
      description='Wraps cli applications to web services',
      author='Alexander Weigl',
      author_email='Alexander.Weigl@student.kit.edu',
      url='https://github.com/CognitionGuidedSurgery/cli2web',
      requires=[ 'Flask', 'Flask-Restful', 'path.py', 'pyclictk' ],
      packages=['cli2web'],
      package_data = { 'cli2web' : ['templates/*']}
)
