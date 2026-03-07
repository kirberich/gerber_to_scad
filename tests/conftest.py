import os


def pytest_configure():
    os.environ.setdefault("DEBUG", "True")
    os.environ.setdefault("SCAD_BINARY", "/usr/bin/openscad")
