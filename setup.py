
try:
    from casket.git import GitInfo
    version = GitInfo('.').get_tag()
except:
    raise RuntimeError("Couldn't find project tag/version")

try:
    from setuptools import setup
except ImportError:
    from distutils.core import setup

setup(
    name='casket',
    packages=['casket'],
    version=version,
    install_requires=[
        'tinydb>=3.2.1'
    ],
    description='Persistent storage for ML experiments',
    author='Enrique Manjavacas',
    author_email='enrique.manjavacas@gmail.com',
    url='https://www.github.com/emanjavacas/casket',
    download_url='https://www.github.com/emanjavacas/casket/tarball/%s' % version,
    keywords=['experiments', 'Machine Learning'],
    classifiers=[]
)
