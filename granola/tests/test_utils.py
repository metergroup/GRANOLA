import os
import shutil

import pytest

from granola.utils import IS_PYTHON3, get_path, fixpath

if IS_PYTHON3:
    from unittest.mock import patch
else:
    from mock import patch


PATHS_TO_TEST = [
    "a\\b\\c\\d.json",
    "a/b/c/d.json",
    r"a\b\c\d.json",
    r"a/b\c/d.json",
    "a/b\\c\\\\d.json",
    "a/b\\c\\\\d.json",
]


ROOT_PATHS_TO_TEST = ["x\\y\\z", "x/y/z", r"x\y\z", r"x\y/z", "x//y\\\\z"]


def test_using_get_path_with_just_a_file_should_return_absolute_path_to_root_to_file():
    # Given a file name
    file = "test.csv"

    # When we call `get_path` on it
    path = get_path(file)

    # Then we should get back the file name located at our root directory
    cwd = os.getcwd()
    true_path = os.path.join(cwd, file)
    assert true_path == path


def test_using_get_path_with_directories_that_dont_exist_should_create_those_directories():
    # Given a path to a file name
    path_to_file = os.path.join("Toby", "Tali", "test.csv")

    # When we call `get_path` on it
    path = get_path(path_to_file)

    # Then it should have created the directories Toby and Tali
    dir_name = os.path.dirname(path)
    assert os.path.isdir(dir_name)

    # cleanup by removing created directories
    shutil.rmtree("Toby")


@pytest.mark.parametrize("path", PATHS_TO_TEST)
@pytest.mark.parametrize(
    "os_name,pathlib_flavor,expected",
    [("nt", "_WindowsFlavour", r"a\b\c\d.json"), ("posix", "_PosixFlavour", r"a/b/c/d.json")],
)
def test_fixpath_normalizes_paths_on_both_windows_and_posix_systems(path, os_name, pathlib_flavor, expected):
    # Given a series of paths in string formats to normalize

    # When we fix their paths on both windows and linux
    with patch("os.name", os_name), patch("pathlib." + pathlib_flavor + ".is_supported", True):
        assert fixpath(path) == expected
    # Then fixpath normalizes the path to the native path style of that os


@pytest.mark.parametrize("path", PATHS_TO_TEST)
@pytest.mark.parametrize("root", ROOT_PATHS_TO_TEST)
@pytest.mark.parametrize(
    "os_name,pathlib_flavor,expected",
    [("nt", "_WindowsFlavour", r"x\y\z\a\b\c\d.json"), ("posix", "_PosixFlavour", r"x/y/z/a/b/c/d.json")],
)
def test_fixpath_takes_joined_paths_on_both_windows_and_posix_systems_and_normalizes_them(
    path, root, os_name, pathlib_flavor, expected
):
    # Given a series of paths and roots in string formats to join and then normalize

    # When we join their paths and then fix their paths on both windows and linux
    with patch("os.name", os_name), patch("pathlib." + pathlib_flavor + ".is_supported", True):
        joined_path = os.path.join(root, path)
        assert fixpath(joined_path) == expected
    # Then their paths are joined and then normalized to the native path style of that os
