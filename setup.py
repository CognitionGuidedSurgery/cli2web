from setuptools import setup, find_packages

setup(name='cli2web',
      version='0.1',
      description='Wraps cli applications to web services',
      author='Alexander Weigl',
      author_email='Alexander.Weigl@student.kit.edu',
      url='https://github.com/CognitionGuidedSurgery/cli2web',
      install_requires=[ 'flask', 'flask_restful', 'path.py', 'pyclictk' ],
      packages=['cli2web'],
      package_data = { 'cli2web' : ['templates/*']},
      entry_points={
        'console_scripts': [
            'cli2web = cli2web:entrypoint'
        ]
      }
)
