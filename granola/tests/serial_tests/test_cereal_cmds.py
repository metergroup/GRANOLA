from granola.tests.conftest import query_device


def test_cereal_w_serial_should_initialize(mock_cereal):
    # Given a mock pyserial class has been initialized

    # When the class is initialized

    # Then it should have a true truth value
    assert mock_cereal


def test_cereal_get_name_should_be_cereal_test_fixture(mock_cereal):
    # Given a mock pyserial class has been initialized

    # When we write the cmd get -name and read the response
    name = query_device(mock_cereal, "get name")

    # Then its response should match the expected response
    true_name = b"Cereal Test Fixture\r"
    assert true_name == name


def test_cereal_get_ver_should_be_000(mock_cereal):
    # Given a mock pyserial class has been initialized

    # When we write the cmd get -ver and read the response
    version = query_device(mock_cereal, "get ver")

    # Then
    assert version == b"0.0.0\r>"


def test_cereal_get_name_then_get_ver_should_be_000(mock_cereal):
    # Given a mock pyserial class has been initialized

    # When we write a command and get the response and then a different command and response
    query_device(mock_cereal, "get name")
    version = query_device(mock_cereal, "get ver")

    # Then its response should match the expected response
    assert version == b"0.0.0\r>"


def test_cereal_multiple_start_should_be_OK(mock_cereal):
    # Given a mock pyserial class has been initialized with a csv with only 1 get -ver cmds

    # When we write the cmd get -name and read the response multiple times
    query_device(mock_cereal, "start")
    query_device(mock_cereal, "start")
    ok = query_device(mock_cereal, "start")

    # Then its response should match the expected response even if the data only has 1 start
    assert ok == b"OK\r>"


def test_cereal_get_volt_should_not_all_be_the_same(mock_cereal):
    # Given a mock pyserial class has been initialized with different get -volt cmds

    # When we query the mock device many times with the cmd get -volt
    volts = []
    for _ in range(10):
        volts.append(query_device(mock_cereal, "get -volt"))

    # Then they shouldn't all be the same
    all_the_same = len(set(volts)) == 1
    assert not all_the_same


def test_cereal_unsupported_command_should_return_ERROR(mock_cereal):
    # Given a mock pyserial class has been initialized

    # When we query with a fake serial command
    response = query_device(mock_cereal, "fake serial command")

    # Then it should respond with error (the unsupported response we set in the config)
    true_response = b"ERROR\r>"
    assert true_response == response
