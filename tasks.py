"""Module of Invoke tasks regarding CODE QUALITY to be invoked from the command line. Try
invoke --list
from the command line for a list of all available commands.
"""
import os
import sys

from invoke import task

is_python_37 = sys.version_info[0] == 3 and sys.version_info[1] == 7
greater_than_36 = sys.version_info > (3, 6)


POSIX = os.name == "posix"


@task
def black(
    command,
):
    """Runs black (autoformatter) on all .py files recursively"""
    if sys.version_info > (3, 6):
        print(
            """
Running Black the Python code formatter
=======================================
"""
        )
        command.run("black .", echo=True, pty=POSIX)
    else:
        print(
            """
Black formatting should be ran on Python 3.7 or higher, skipping
================================================================
"""
        )


@task
def isort(
    command,
):
    """Runs isort (import sorter) on all .py files recursively"""
    if POSIX or sys.version_info > (3,):
        print(
            """
Running isort the Python code import sorter
===========================================
"""
        )
        command.run("isort .", echo=True, pty=POSIX)
    else:
        print(
            """
On Windows, isort import sorter should be ran on Python 3, skipping
===================================================================
"""
        )


@task
def lint(
    command,
):
    """Runs flake8 (linter) on all .py files recursively"""
    print(
        """
Running flake8 a Python code linter
===================================
"""
    )
    command.run("flake8", echo=True, pty=POSIX)


@task(pre=[black, isort, lint])
def style(
    command,
):
    """Runs black, isort, and flake8
    Arguments:
        command {[type]} -- [description]
    """
    # If we get to this point all tests listed in 'pre' have  passed
    # unless we have run the task with the --warn flag
    if not command.config.run.warn:
        print(
            """
All Style Checks Passed Successfully
====================================
"""
        )


@task
def pytest(
    command,
):
    """Runs pytest to identify failing tests and doctests"""

    print(
        """
Running pytest the test framework
=================================
"""
    )
    command.run("python -m pytest .", echo=True, pty=POSIX)


@task
def docs(
    command,
):
    """Runs Sphinx to build the docs locally for testing"""

    print(
        """
Running Sphinx to test the docs building
========================================
"""
    )
    command.run("sphinx-build -b html docs docs/_build/html", echo=True, pty=POSIX)


@task(pre=[black, isort, lint, pytest, docs])
def all(
    command,
):
    """Runs black, isort, flake8, and pytest
    Arguments:
        command {[type]} -- [description]
    """
    # If we get to this point all tests listed in 'pre' have passed
    # unless we have run the task with the --warn flag
    if not command.config.run.warn:
        print(
            """
All Style Checks Tests Passed Successfully
==========================================
"""
        )
