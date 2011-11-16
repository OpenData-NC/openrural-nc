try:
    from setuptools import setup, find_packages
except ImportError:
    from ez_setup import use_setuptools
    use_setuptools()
    from setuptools import setup, find_packages

setup(
    name='openrural',
    version="0.1",
    author='Caktus Consulting Group, LLC',
    author_email='solutions@caktusgroup.com',
    description="An OpenBlock implemention for rural NC",
    license="GPLv3",
    install_requires=[
    "ebpub",
    "ebdata",
    "obadmin",
    ],
    dependency_links=[
    ],
    packages=find_packages(exclude=['ez_setup']),
    include_package_data=True,
    entry_points="""
    """,
)
