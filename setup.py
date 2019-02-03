from setuptools import setup

setup(
    name="graphotype",
    python_requires='>=3.6.0',
    packages=['graphotype', 'graphotype.import_schema'],
    package_data={'graphotype.import_schema': ['templates/*.py.tmpl']},
    version='0.0.1',
    install_requires=[
        'graphql-core>=2.1',
        'dataclasses; python_version == "3.6"',
        'typing-inspect',
    ]
)
