from setuptools import setup, find_packages
 
setup(name='django-sqlviews',
    version="1.0",
    description='Management command for creating views of multi-table models',
    author='Dennis Kaarsemaker',
    author_email='dennis@kaarsemaker.net',
    url='http://github.com/seveas/django-sqlviews',
    packages=find_packages(),
    classifiers=[
        "Framework :: Django",
        "Intended Audience :: Developers",
        "Operating System :: OS Independent",
        "Topic :: Software Development"
    ],
)
