from setuptools import setup

setup(
    name="pypopquiz",
    version="0.1.0",
    author="Cedric Nugteren",
    url="https://github.com/CNugteren/pypopquiz",
    description="Python tool to create pop-quiz videos programmatically",
    license="MIT",
    install_requires=["ffmpeg-python", "pytube", "jsonschema", "moviepy"],
    scripts=["pypopquiz/popquiz.py"],
    classifiers=[
        'Development Status :: 4 - Beta',
        'Intended Audience :: Public',
        'Topic :: Software Development :: Libraries',
        'License :: OSI Approved :: MIT License',
        'Programming Language :: Python :: 3',
    ],
    keywords="popquiz"
)
