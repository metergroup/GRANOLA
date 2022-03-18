"""Module of Invoke tasks regarding CODE QUALITY to be invoked from the command line. Try
invoke --list
from the command line for a list of all available commands.
"""

from invoke import task


@task
def black(
    command,
):
    """Runs black (autoformatter) on all .py files recursively"""
    print(
        """
Running Black the Python code formatter
=======================================
"""
    )
    command.run(
        "black .",
        echo=True,
    )


@task
def isort(
    command,
):
    """Runs isort (import sorter) on all .py files recursively"""
    print(
        """
Running isort the Python code import sorter
===========================================
"""
    )
    command.run(
        "isort .",
        echo=True,
    )


@task
def flake8(
    command,
):
    """Runs flake8 (linter) on all .py files recursively"""
    print(
        """
Running flake8 a Python code linter
===================================
"""
    )
    command.run(
        "flake8",
        echo=True,
    )


@task(pre=[black, isort, flake8])
def style(
    command,
):
    """Runs black, isort, and flake8
    Arguments:
        command {[type]} -- [description]
    """
    # If we get to this point all tests listed in 'pre' have passed
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
    command.run("python -m pytest", echo=True, pty=True)


@task(pre=[black, isort, flake8, pytest])
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