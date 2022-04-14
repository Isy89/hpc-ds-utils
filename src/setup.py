from setuptools import find_packages, setup

# get the dependencies and installs
with open("requirements.txt", "r", encoding="utf-8") as f:
    requires = []
    for line in f:
        req = line.split("#", 1)[0].strip()
        requires.append(req)

setup(
    name="hpc_ds_utils",
    version="0.1",
    author="Isaac Lazzeri",
    description="A set of tools to make life of researcher using hpc easier",
    url="https://github.com/isy89/hpc-ds-utils",
    packages=find_packages(),
    entry_points={
        "console_scripts": [
            "jpc = hpc_ds_utils.jlab_connector:main_func",
            "start_jpc_interactive_session = hpc_ds_utils.start_jpc_interactive_session:main_jpc_interactive"
        ]
    },
    install_requires=requires,
    python_requires=">=3.6",
    extras_require={},
)
