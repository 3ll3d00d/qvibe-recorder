from setuptools import setup, find_packages

with open('README.rst') as f:
    readme = f.read()

with open('LICENSE') as f:
    license = f.read()


setup(name='qvibe-recorder',
      version='0.1.0',
      description='Bridges data to/from a mpu6050 to a tcp socket',
      long_description=readme,
      classifiers=[
          'License :: OSI Approved :: MIT License',
          'Programming Language :: Python :: 3.7'
      ],
      url='http://github.com/3ll3d00d/qvibe-recorder',
      author='Matt Khan',
      author_email='mattkhan+qvibe-recorder@gmail.com',
      license=license,
      packages=find_packages(exclude=('test', 'docs')),
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
