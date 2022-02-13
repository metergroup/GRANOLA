from granola.tests.conftest import query_device


def test_sensor_post_should_be_Code_Good(mock_cereal):
    # Given a mock pyserial class has been initialized with a default serial cmd csv
    # and a separate csv for sdi sensor commads

    # When we query the commands just like any other commands
    post_cmd = "sdicmd 1 e"
    post = query_device(mock_cereal, post_cmd)

    # Then it shouldn't matter if we set  up the class to tell it which csv to go to,
    # its response should match the expected response
    true_post = b"1 Good\r\n\r>"
    assert true_post == post


def test_sensor_get_measurement_repeatedly_should_be_different(mock_cereal):
    # Given a mock pyserial class has been initialized with a sdi sensor csv
    # of sensor commands of different values for a certain command

    # When we query the mock device many times with the cmd a get measurement command
    get_measurement_cmd = "sdicmd 1 get-measurement"
    measurements = []
    for _ in range(10):
        measurements.append(query_device(mock_cereal, get_measurement_cmd))

    # Then they should have multiple responses
    all_the_same = len(set(measurements)) == 1
    assert not all_the_same
