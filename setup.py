from setuptools import setup, find_packages

setup(
    name='material_parser',
    packages=find_packages(),
    version='6.1.2',
    author='Synthesis Project Team',
    author_email='0lgaGkononova@yandex.ru',
    description='Material Synthesis Project',
    zip_safe=False,
    install_requires=[
        "regex",
        "pubchempy",
        "sympy",
    ],
    include_package_data=True
)
