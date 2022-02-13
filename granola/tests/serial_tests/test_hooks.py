import logging
import time

import pytest

from numpy.testing import assert_almost_equal

from granola import Cereal, CannedQueries, ApproachHook, LoopCannedQueries, StickCannedQueries, register_hook, HookTypes
from granola.tests.conftest import CONFIG_PATH, query_device, decode_response

logger = logging.getLogger(__name__)


def test_loop_hook_should_loop_included_queries_only():
    # Given a mock serial with loop hook to loop over get batt\r
    loop_hook = LoopCannedQueries(attributes={"get batt\r"}, include_or_exclude="include")

    bk_cereal = Cereal.mock_from_file("cereal", config_path=CONFIG_PATH, hooks=[loop_hook])

    # When we query a command not in our looping commands that is only entered once,
    bk_cereal.write(b"start\r")
    non_looped_1st_response = bk_cereal.read(100)

    # and we query our looped command over again
    for _ in range(10):
        bk_cereal.write(b"get batt\r")
        looped_response = bk_cereal.read(100)
        looped_true_response = b"100\r>"

        # as well as query our non looped command again
        bk_cereal.write(b"start\r")
        non_looped_response = bk_cereal.read(100)
        non_looped_unsupported_response = b"ERROR\r>"

        # Then the looped response keeps looping
        assert looped_true_response == looped_response
        # and the non looping response gives us unsupported response
        assert non_looped_unsupported_response == non_looped_response

    # and our initial non looped response was ok
    non_looped_true_1st_response = b"OK\r>"
    assert non_looped_true_1st_response == non_looped_1st_response


def test_loop_hook_should_not_loop_excluded_queries():
    # Given a mock serial with loop hook to not loop over get batt\r, but no other excluded queries
    loop_hook = LoopCannedQueries(attributes={"get batt\r"}, include_or_exclude="exclude")

    bk_cereal = Cereal.mock_from_file("cereal", config_path=CONFIG_PATH, hooks=[loop_hook])

    # When we query a our excluded response
    bk_cereal.write(b"get batt\r")
    non_looped_1st_response = bk_cereal.read(100)

    # and we query our looped command over again
    for _ in range(10):
        bk_cereal.write(b"start\r")
        looped_response = bk_cereal.read(100)
        looped_true_response = b"OK\r>"

        # as well as query our non looped command again
        bk_cereal.write(b"get batt\r")
        non_looped_response = bk_cereal.read(100)
        non_looped_unsupported_response = b"ERROR\r>"

        # Then the looped response keeps looping
        assert looped_true_response == looped_response
        # and the non looping response gives us unsupported response
        assert non_looped_unsupported_response == non_looped_response

    # and our initial non looped response was ok
    non_looped_true_1st_response = b"100\r>"
    assert non_looped_true_1st_response == non_looped_1st_response


def test_loop_hook_with_no_commands_included_should_return_unsupported_after_loop_end():
    # Given a mock serial with loop hook to include no commands
    loop_hook = LoopCannedQueries(attributes=set(), include_or_exclude="include")

    bk_cereal = Cereal.mock_from_file("cereal", config_path=CONFIG_PATH, hooks=[loop_hook])

    # When we query any command
    bk_cereal.write(b"get batt\r")
    non_looped_1st_response = bk_cereal.read(100)

    # and we query it to get past the generator
    for _ in range(10):

        bk_cereal.write(b"get batt\r")
        non_looped_response = bk_cereal.read(100)
        non_looped_unsupported_response = b"ERROR\r>"

        # Then the non looping response gives us unsupported response
        assert non_looped_unsupported_response == non_looped_response

    # and our initial non looped response was ok
    non_looped_true_1st_response = b"100\r>"
    assert non_looped_true_1st_response == non_looped_1st_response


def test_loop_hook_with_cmd_that_is_excluded_should_log_a_warning_msg(caplog):
    # Given a mock serial with loop hook to not loop over get batt\r, but no other excluded queries
    loop_hook = LoopCannedQueries(attributes={"get batt\r"}, include_or_exclude="exclude")

    bk_cereal = Cereal.mock_from_file("cereal", config_path=CONFIG_PATH, hooks=[loop_hook])

    # When we query a our excluded response past the generator
    for _ in range(10):
        with caplog.at_level(logging.WARNING):
            bk_cereal.write(b"get batt\r")
            bk_cereal.read(100)

    # Then we capture in our log that there was an unhandled response from the hooks
    assert "unhandled response return from hooks" in caplog.text


def test_stick_hook_should_stick_on_command_after_the_generator_expires():
    # Given a mock serial with the stick hook to stick on adc30 3\r after the generator expires
    stick_hook = StickCannedQueries(attributes={"scan adc30 3\r"}, include_or_exclude="include")

    bk_cereal = Cereal.mock_from_file("cereal", config_path=CONFIG_PATH, hooks=[stick_hook])

    # When we query it enough to ensure it has exhausted the generator
    for _ in range(50):
        bk_cereal.write(b"scan adc30 3\r")
        bk_cereal.read(100)

    responses = set()
    # Then all future queries should be the same
    for _ in range(10):
        bk_cereal.write(b"scan adc30 3\r")
        responses.add(bk_cereal.read(100))

        assert len(responses) == 1


def test_approach_hook_should_set_a_greater_value_and_subsequent_gets_should_increase():
    # Given a mock serial with the approach hook defined for temp attribute
    approach_hook = ApproachHook(attributes={"temp"}, include_or_exclude="include")

    bk_cereal = Cereal.mock_from_file("cereal", config_path=CONFIG_PATH, hooks=[approach_hook])

    # When we set the temperature higher
    query_device(bk_cereal, "set -temp 25")
    # and then query it repeatedly
    old_value = float(query_device(bk_cereal, "get -temp")[:-2])
    for _ in range(5):
        time.sleep(0.001)
        # we grab the numeric part of the temp, leaving behind the write terminator
        new_value = float(query_device(bk_cereal, "get -temp")[:-2])

        # then each new value is strictly larger than the old value
        assert new_value > old_value


def test_approach_hook_should_not_impact_attributes_not_specified():
    # Given a mock serial with the approach hook defined for temp attribute
    approach_hook = ApproachHook(attributes={"temp"}, include_or_exclude="include")

    bk_cereal = Cereal.mock_from_file("cereal", config_path=CONFIG_PATH, hooks=[approach_hook])

    # When we set the sn
    query_device(bk_cereal, "set -sn 123456789")
    # and then query it repeatedly
    for _ in range(5):
        time.sleep(0.001)
        sn = query_device(bk_cereal, "get -sn")

        # then the sn should still be the same
        true_response = "123456789\r>"
        decoded_sn = decode_response(sn, bk_cereal)
        assert true_response == decoded_sn


def test_approach_hook_should_reach_a_certain_value():
    # Given a mock serial with the approach hook defined for temp attribute and time increase each degree 0.1 seconds
    time_for_1_degree = 0.1

    approach_hook = ApproachHook(
        attributes={"temp"}, include_or_exclude="include", transition_asc_scaling=time_for_1_degree
    )

    bk_cereal = Cereal.mock_from_file("cereal", config_path=CONFIG_PATH, hooks=[approach_hook])

    # When we set the temperature 1 degree higher
    degree_pls_1 = float(query_device(bk_cereal, "get -temp")[:-2]) + 1
    query_device(bk_cereal, "set -temp {degree_pls_1}".format(degree_pls_1=degree_pls_1))

    # and we wait time_for_1_degree seconds (and some extra because it is an asymptotic function to approach the value)
    # and get the temp
    time.sleep(time_for_1_degree + 0.01)
    value = float(query_device(bk_cereal, "get -temp")[:-2])

    # Then the the the temp should be degree_pls_1 degrees
    assert_almost_equal(degree_pls_1, value, decimal=3)


def test_approach_hook_should_throw_ValueError_if_you_use_it_on_a_non_numeric_attribute():
    # Given a mock serial with the approach hook defined for sn attribute
    approach_hook = ApproachHook(attributes={"sn"}, include_or_exclude="include")

    bk_cereal = Cereal.mock_from_file("cereal", config_path=CONFIG_PATH, hooks=[approach_hook])

    # When we set the sn, which is a query in the approach hook
    with pytest.raises(ValueError):
        query_device(bk_cereal, "set -sn sn1234")
        # Then it should error out because the default sn isn't a float type


def test_approach_hook_should_not_work_for_if_you_exclude_a_query():
    # Given a mock serial with the approach hook defined to exclude temp
    approach_hook = ApproachHook(attributes={"temp"}, include_or_exclude="exclude")

    bk_cereal = Cereal.mock_from_file("cereal", config_path=CONFIG_PATH, hooks=[approach_hook])

    # When we set the temperature higher (instantly since it is excluding temp)
    query_device(bk_cereal, "set -temp 25")
    # and then query it repeatedly
    for _ in range(5):
        time.sleep(0.001)
        # we grab the numeric part of the temp, leaving behind the write terminator
        new_value = float(query_device(bk_cereal, "get -temp")[:-2])

        # then each new value is the same as the old value
        assert new_value == 25


def test_approach_hook_should_work_for_if_you_use_a_attribute_not_excluded():
    # Given a mock serial with the approach hook defined to exclude temp
    approach_hook = ApproachHook(attributes={"sn"}, include_or_exclude="exclude")

    bk_cereal = Cereal.mock_from_file("cereal", config_path=CONFIG_PATH, hooks=[approach_hook])

    # When we set the temperature higher (not instantly since it is doesn't exclude temp)
    query_device(bk_cereal, "set -temp 25")
    # and then query it repeatedly
    old_value = float(query_device(bk_cereal, "get -temp")[:-2])
    for _ in range(5):
        time.sleep(0.001)
        # we grab the numeric part of the temp, leaving behind the write terminator
        new_value = float(query_device(bk_cereal, "get -temp")[:-2])

        # then each new value is strictly larger than the old value
        assert new_value > old_value


def test_a_func_registered_as_a_hook_can_have_the_first_arg_as_self_or_not_and_a_hook_doesnt_need_to_be_initialized():
    # Given two functions two turn into hooks, one with self and one without self
    @register_hook(hook_type_enum=HookTypes.post_reading, hooked_classes=[CannedQueries])
    def hook1(self, hooked, result, data, **kwargs):
        return "1"

    @register_hook(hook_type_enum=HookTypes.post_reading, hooked_classes=[CannedQueries])
    def hook2(hooked, result, data, **kwargs):
        return "2"

    # when we initialize 2 different mock serials, one with the first hook and one with the second
    bk_cereal1 = Cereal.mock_from_file("cereal", config_path=CONFIG_PATH, hooks=[hook1])

    bk_cereal2 = Cereal.mock_from_file("cereal", config_path=CONFIG_PATH, hooks=[hook2])

    # and we query anything from the devices
    response1 = query_device(bk_cereal1, "any command")
    response2 = query_device(bk_cereal2, "any command")

    # then both hooks return what we expect
    assert response1 == b"1"
    assert response2 == b"2"


def test_getter_setter_response_can_be_templated():
    # Given a mock serial with getters and setters defined for temp attribute, and set temp returning temp
    bk_cereal = Cereal.mock_from_file("cereal", config_path=CONFIG_PATH)
    volts = 3000
    temp = 100

    # When we query the device with getters and setters that calculate their response
    query_device(bk_cereal, "set -temp %s" % temp)
    volt_calc = query_device(bk_cereal, "set volt %s" % volts)
    volt_temp = query_device(bk_cereal, "get volt_temp")

    # Then our queries will be templated with the config defined calculation
    assert volt_calc == b"Volt Calculation %s" % str(float(volts) / 2.0).encode("utf-8")
    volt_temp_calc = float(temp + volts) / 2.0
    assert volt_temp == str(volt_temp_calc).encode("utf-8")
