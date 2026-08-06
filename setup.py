from setuptools import setup, find_packages

setup(
    name="memory-vault",
    version="1.0.1",
    description="Multi-device backup and sync tool for Linux with Rclone and Restic",
    long_description=open("README.md").read(),
    long_description_content_type="text/markdown",
    author="Daniquir",
    author_email="daniquir@users.noreply.github.com",
    url="https://github.com/Daniquir/memory-vault",
    project_urls={
        "Bug Tracker": "https://github.com/Daniquir/memory-vault/issues",
        "Documentation": "https://github.com/Daniquir/memory-vault/blob/main/docs/",
        "Source Code": "https://github.com/Daniquir/memory-vault",
    },
    license="MIT",
    # vault.py is the console entry module; must be listed explicitly.
    # Modern editable installs (PEP 660) no longer put the project root on
    # sys.path, so omitting py_modules breaks `vault` on Fedora/newer pip.
    py_modules=["vault"],
    packages=find_packages(exclude=["tests", "tests.*"]),
    include_package_data=True,
    install_requires=[
        "customtkinter>=5.2.0",
        "pystray>=0.19.5",
        "Pillow>=10.0.0",
        "boto3>=1.28.0",
    ],
    entry_points={
        "console_scripts": [
            "vault=vault:main_entry",
        ],
    },
    python_requires=">=3.7",
    keywords=[
        "backup",
        "sync",
        "rclone",
        "restic",
        "wasabi",
        "s3",
        "encryption",
        "linux",
        "cloud-storage",
        "snapshot",
    ],
    classifiers=[
        "Development Status :: 4 - Beta",
        "Intended Audience :: End Users/Desktop",
        "Intended Audience :: System Administrators",
        "License :: OSI Approved :: MIT License",
        "Natural Language :: English",
        "Natural Language :: Spanish",
        "Operating System :: POSIX :: Linux",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.7",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Programming Language :: Python :: 3.12",
        "Programming Language :: Python :: 3.13",
        "Programming Language :: Python :: 3.14",
        "Topic :: System :: Archiving :: Backup",
        "Topic :: System :: Filesystems",
        "Topic :: Utilities",
    ],
)
