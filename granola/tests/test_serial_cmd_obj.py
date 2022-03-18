import pandas as pd

from granola import CannedQueries, Cereal, RandomizeResponse
from granola.tests.conftest import (
    CONFIG_PATH,
    all_equal,
    assert_filled_all,
    query_device,
)


def test_that_you_can_pass_canned_queries_directly_instead_of_as_file_paths(canned_queries_command_readers):
    # Given a mock pyserial class defined by a python dictionary configuration with canned queries directly

    # When we initialize it
    mock = Cereal(command_readers=canned_queries_command_readers)()
    # and query it
    one = query_device(mock, "1")

    # Then we get the expected result
    assert one == b"1"


def test_that_you_can_pass_canned_queries_directly_with_multiple_response(canned_queries_command_readers):
    # Given a mock pyserial class defined by a python dictionary configuration with canned queries directly

    # When we initialize it
    mock = Cereal(command_readers=canned_queries_command_readers)()
    # and issue get temp twice
    a4 = query_device(mock, "4")
    b4 = query_device(mock, "4")

    # Then we should get different responses
    assert a4 == b"4a"
    assert b4 == b"4b"


def test_that_you_can_pass_canned_queries_directly_with_multiple_commands(canned_queries_command_readers):
    # Given a mock pyserial class defined by a python dictionary configuration with canned queries directly

    # When we initialize it
    mock = Cereal(command_readers=canned_queries_command_readers)()
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
    mock = Cereal.mock_from_json("dictionary", config_path=CONFIG_PATH)()
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
    command_readers = {
        "CannedQueries": {
            "data": [{"1\r": "1", "2\r": {"response": "3", "delay": 3}}],
        }
    }

    # When we initialize it
    mock = Cereal(command_readers=command_readers)()
    df = mock._readers_["CannedQueries"].serial_df

    # Then 2 has a delay of 3 but get -sn does not have any delay (nan)
    assert_filled_all(df.loc[(df.cmd == "2\r")]["delay"] == 3)
    assert_filled_all(df.loc[(df.cmd == "1\r")]["delay"].isna())


def test_that_you_can_specify_a_delay_on_one_command_and_a_broadcasting_delay_for_the_rest(
    canned_queries_command_readers,
):
    # Given a dictionary canned queries with a default delay and a specific delay

    # When we initialize it
    mock = Cereal(command_readers=canned_queries_command_readers)()
    df = mock._readers_["CannedQueries"].serial_df

    # Then 3 gets the default delay of 3, but 2 has a delay of 0 since we that is the default
    assert_filled_all(df.loc[(df.cmd == "3\r")]["delay"] == 3)
    assert_filled_all(df.loc[(df.cmd == "2\r")]["delay"] == 0)


def test_that_you_can_specify_a_inside_a_response_list(canned_queries_command_readers):
    # Given a dictionary canned queries with a default delay and a specific delay

    # When we initialize it
    mock = Cereal(command_readers=canned_queries_command_readers)()
    df = mock._readers_["CannedQueries"].serial_df

    # THen the delays inside lists should specify columns
    assert_filled_all(df.loc[(df.cmd == "1\r")]["delay"] == 0)
    assert_filled_all(df.loc[(df.cmd == "3\r")]["delay"] == 3)
    assert_filled_all(df.loc[(df.cmd == "7\r") & (df.response == "7a")]["delay"] == 7)
    assert_filled_all(df.loc[(df.cmd == "7\r") & (df.response == "7b")]["delay"] == 0)


def test_that_that_all_off_the_ways_to_specify_canned_queries_inside_dicts_can_go_together(
    canned_queries_command_readers,
):
    # Given a dictionary canned queries with a default delay and a specific delay

    # When we initialize it
    mock = Cereal(command_readers=canned_queries_command_readers)()
    df = mock._readers_["CannedQueries"].serial_df

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


def test_random_responses():
    # When we have a dataframe and and randomized response enum
    df = pd.DataFrame(data=dict(cmd=[1, 2, 3], response=[1, 2, 3]))
    will_randomize_responses = RandomizeResponse.randomized_w_replacement.name

    # When we randomize our response 100 times
    # (we choose 100, just to be pretty sure that it will give us difference respones, even if luck isn't on our side)
    randomized_responses = []
    for _ in range(100):
        randomized_responses.append(next(CannedQueries._get_generator_from_df(df.copy(), will_randomize_responses)))

    # instead of always getting the 1st response, we should get others as well
    assert len(set(randomized_responses)) != 1


def test_random_responses_with_removal():

    # When we have a dataframe and and randomized response enum
    df = pd.DataFrame(data=dict(cmd=[1, 2, 3], response=[1, 2, 3]))
    will_randomize_responses = RandomizeResponse.randomize_and_remove.name

    # When we randomize our response 100 times
    # (we choose 100, just to be pretty sure that it will give us difference respones, even if luck isn't on our side)
    randomized_responses = []
    for _ in range(100):
        responses = []
        for _ in range(len(df)):
            responses.append(next(CannedQueries._get_generator_from_df(df.copy(), will_randomize_responses)))
        randomized_responses.append(responses)

    # instead of always getting the 1st response, we should get others as well
    for responses in randomized_responses:
        assert len(responses) == 3
    assert not all_equal(randomized_responses)


def test_pass_in_randomize_response_in_canned_queries():
    # Given a CannedQueries config with a randomized responses
    command_readers = {
        "CannedQueries": {"data": [{"1\r": ["1a", "1b", "1c"]}], "will_randomize_responses": "randomized_w_replacement"}
    }

    # When we query the entire list of our 1\r command 100 times
    # (we choose 100, just to be pretty sure that it will give us difference respones, even if luck isn't on our side)
    randomized_responses = []
    for _ in range(100):
        mock = Cereal(command_readers=command_readers)()
        responses = []
        for _ in range(3):
            responses.append(query_device(mock, "1"))
        randomized_responses.append(responses)

    # Then the order the 3 respones is not the same accross all 100 tries
    assert not all_equal(randomized_responses)
