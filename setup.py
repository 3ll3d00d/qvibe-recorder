import os
from setuptools import setup, find_packages

with open('README.md') as f:
    readme = f.read()

version = os.environ.get('TRAVIS_TAG', '0.0.1-alpha.1+dirty')

setup(name='qvibe-recorder',
      version=version,
      description='Bridges data to/from a mpu6050 to a tcp socket',
      long_description=readme,
      long_description_content_type='text/markdown',
      classifiers=[
          'License :: OSI Approved :: MIT License',
          'Programming Language :: Python :: 3.7',
          'Development Status :: 4 - Beta',
      ],
      url='http://github.com/3ll3d00d/qvibe-recorder',
      author='Matt Khan',
      author_email='mattkhan+qvibe-recorder@gmail.com',
      license='MIT',
      packages=find_packages(exclude=('test', 'docs')),
      python_requires='>=3.7',
      entry_points={
          'console_scripts': [
              'qvibe-recorder = qvibe.app:run',
          ],
      },
      install_requires=[
          'smbus2',
          'pyyaml',
          'twisted'
      ],
      setup_requires=[
          'pytest-runner'
      ],
      tests_require=[
          'pytest'
      ],
      include_package_data=False,
      zip_safe=False)
