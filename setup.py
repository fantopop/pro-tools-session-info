from setuptools import setup, find_packages
import session

with open('README.md', 'r') as f:
    long_description = f.read()

setup(
    name='pro-tools-session-info',
    version='0.1',
    author='Ilya Putilin',
    author_email='fantopop@gmail.com',
    description='Read Session Info as Text files exported from Avid Pro Tools',
    long_description=long_description,
    long_description_content_type='text/markdown',
    url='https://github.com/fantopop/pro-tools-session-info',
    packages=find_packages(),
    classifiers=[
        'Programming Language :: Python',
        'License :: OSI Approved :: MIT License',
        'Operating System :: OS Independent',
        'Natural Language :: English',
        'Topic :: Multimedia :: Sound/Audio',
        'Topic :: Software Development :: Libraries'
    ],
    python_requires='>=3.6',
    install_requires=[
        'pandas',
        'timecode'
    ],
    keywords=['audio', 'daw', 'edl']
)