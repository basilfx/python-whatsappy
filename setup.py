from setuptools import setup

# Setup definitions
setup(
    name="python-whatsappy",
    version="3.0.0",
    description="An unoffical Python API for connecting with the WhatsApp "
                "chat protocol.",
    author="Bas Stottelaar",
    py_modules=["whatsappy"],
    install_requires=["pbkdf2"],
    license="MIT",
    test_suite="tests",
    classifiers=[
        "Development Status :: 4 - Beta",
        "Intended Audience :: Developers",
        "License :: OSI Approved :: MIT License",
        "Topic :: System :: Networking",
        "Programming Language :: Python :: 2",
        "Programming Language :: Python :: 2.7",
    ]
)
