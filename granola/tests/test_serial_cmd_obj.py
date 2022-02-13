from granola import Cereal
from granola.tests.conftest import CONFIG_PATH, assert_filled_all, query_device


def test_that_you_can_pass_canned_queries_directly_instead_of_as_file_paths(canned_queries_config):
    # Given a mock pyserial class defined by a python dictionary configuration with canned queries directly

    # When we initialize it
    mock = Cereal(config=canned_queries_config)()
    # and query it
    one = query_device(mock, "1")

    # Then we get the expected result
    assert one == b"1"


def test_that_you_can_pass_canned_queries_directly_with_multiple_response(canned_queries_config):
    # Given a mock pyserial class defined by a python dictionary configuration with canned queries directly

    # When we initialize it
    mock = Cereal(config=canned_queries_config)()
    # and issue get temp twice
    a4 = query_device(mock, "4")
    b4 = query_device(mock, "4")

    # Then we should get different responses
    assert a4 == b"4a"
    assert b4 == b"4b"


def test_that_you_can_pass_canned_queries_directly_with_multiple_commands(canned_queries_config):
    # Given a mock pyserial class defined by a python dictionary configuration with canned queries directly

    # When we initialize it
    mock = Cereal(config=canned_queries_config)()
    # and issue all of our serial commands
    a4 = query_device(mock, "4")
    b4 = query_device(mock, "4")
    one = query_device(mock, "1")
    a6 = query_device(mock, "6")

    # Then we should the specified responses
    assert a4 == b"4a"
    assert b4 == b"4b"
    assert one == b"1"
    assert a6 == b"6a"


def test_that_you_can_pass_canned_queries_directly_with_multiple_commands_from_json():
    # Given a mock pyserial class defined by a json dictionary configuration with canned queries directly

    # When we initialize it
    mock = Cereal.mock_from_file("dictionary", config_path=CONFIG_PATH)()
    # and issue all of our serial commands
    twenty = query_device(mock, "get -temp")
    twenty_two = query_device(mock, "get -temp")
    sn1234 = query_device(mock, "get -sn")
    ok = query_device(mock, "test -off")

    # Then we should the specified responses
    assert twenty == b"20\r>"
    assert twenty_two == b"22\r>"
    assert sn1234 == b"sn1234\r>"
    assert ok == b"OK\r>"


def test_that_you_can_specify_a_delay_on_one_command():
    # Given a dictionary canned queries with a delay on only one command
    config = {
        "canned_queries": {
            "data": {"`DEFAULT`": {"1\r": "1", "2\r": {"response": "3", "delay": 3}}},
        }
    }

    # When we initialize it
    mock = Cereal(config=config)()
    df = mock._readers["CannedQueries"].serial_dfs["`DEFAULT`"]

    # Then 2 has a delay of 3 but get -sn does not have any delay (nan)
    assert_filled_all(df.loc[(df.cmd == "2\r")]["delay"] == 3)
    assert_filled_all(df.loc[(df.cmd == "1\r")]["delay"].isna())


def test_that_you_can_specify_a_delay_on_one_command_and_a_broadcasting_delay_for_the_rest(canned_queries_config):
    # Given a dictionary canned queries with a default delay and a specific delay

    # When we initialize it
    mock = Cereal(config=canned_queries_config)()
    df = mock._readers["CannedQueries"].serial_dfs["`DEFAULT`"]

    # Then 3 gets the default delay of 3, but 2 has a delay of 0 since we that is the default
    assert_filled_all(df.loc[(df.cmd == "3\r")]["delay"] == 3)
    assert_filled_all(df.loc[(df.cmd == "2\r")]["delay"] == 0)


def test_that_you_can_specify_a_inside_a_response_list(canned_queries_config):
    # Given a dictionary canned queries with a default delay and a specific delay

    # When we initialize it
    mock = Cereal(config=canned_queries_config)()
    df = mock._readers["CannedQueries"].serial_dfs["`DEFAULT`"]

    # THen the delays inside lists should specify columns
    assert_filled_all(df.loc[(df.cmd == "1\r")]["delay"] == 0)
    assert_filled_all(df.loc[(df.cmd == "3\r")]["delay"] == 3)
    assert_filled_all(df.loc[(df.cmd == "7\r") & (df.response == "7a")]["delay"] == 7)
    assert_filled_all(df.loc[(df.cmd == "7\r") & (df.response == "7b")]["delay"] == 0)


def test_that_that_all_off_the_ways_to_specify_canned_queries_inside_dicts_can_go_together(canned_queries_config):
    # Given a dictionary canned queries with a default delay and a specific delay

    # When we initialize it
    mock = Cereal(config=canned_queries_config)()
    df = mock._readers["CannedQueries"].serial_dfs["`DEFAULT`"]

    # THen we should get get the delays inside lists should specify columns
    assert_filled_all(df.loc[(df.cmd == "1\r")]["delay"] == 0)
    assert_filled_all(df.loc[(df.cmd == "2\r")]["delay"] == 0)
    assert_filled_all(df.loc[(df.cmd == "3\r")]["delay"] == 3)
    assert_filled_all(df.loc[(df.cmd == "4\r")]["delay"] == 0)
    assert_filled_all(df.loc[(df.cmd == "5\r")]["delay"] == 5)
    assert_filled_all(df.loc[(df.cmd == "6\r") & (df.response == "6a")]["delay"] == 6.1)
    assert_filled_all(df.loc[(df.cmd == "6\r") & (df.response == "6b")]["delay"] == 6.2)
    assert_filled_all(df.loc[(df.cmd == "7\r") & (df.response == "7a")]["delay"] == 7)
    assert_filled_all(df.loc[(df.cmd == "7\r") & (df.response == "7b")]["delay"] == 0)
    assert_filled_all(df.loc[(df.cmd == "8\r") & (df.response == "8a")]["delay"] == 8.1)
    assert_filled_all(df.loc[(df.cmd == "8\r") & (df.response == "8b")]["delay"] == 8)
    assert_filled_all(df.loc[(df.cmd == "9\r") & (df.response == "9a")]["delay"] == 9)
    assert_filled_all(df.loc[(df.cmd == "9\r") & (df.response == "9b")]["delay"] == 0)
