import setuptools

with open("README.md", "r") as fh:
    long_description = fh.read()

setuptools.setup(
    name="dlconfig", # Replace with your own username
    version="0.0.1",
    author="dlconfig contributors",
    author_email="dlconfig@example.com",
    description="Deep learning configuration",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/zhreshold/dlconfig",
    packages=setuptools.find_packages(),
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
    ],
    python_requires='>=3.6',
    install_requires=[
        'pyyaml',
        'dataclasses;python_version<"3.7"'],
)
