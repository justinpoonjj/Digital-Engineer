import pytest

from calculator import add, divide, input_validation, multiply, power, subtract


def test_add_positive_numbers():
    assert add(2, 3) == 5

def test_add_negative_numbers():
    assert add(-1, -1) == -2

def test_subtract_positive_numbers():
    assert subtract(5, 3) == 2

def test_subtract_negative_numbers():
    assert subtract(-2, -4) == 2

def test_multiply_positive_numbers():
    assert multiply(2, 3) == 6

def test_multiply_negative_numbers():
    assert multiply(-1, -1) == 1

def test_divide_positive_numbers():
    assert divide(6, 3) == 2

def test_divide_negative_numbers():
    assert divide(-4, 2) == -2

def test_divide_by_zero():
    with pytest.raises(ValueError):
        divide(5, 0)

def test_power_positive_exponents():
    assert power(2, 3) == 8

def test_power_zero_exponent():
    assert power(5, 0) == 1

def test_power_negative_exponents():
    assert power(2, -3) == 0.125

def test_input_validation_integers():
    assert input_validation(5)

def test_input_validation_floats():
    assert input_validation(3.14)

def test_input_validation_non_numbers():
    assert not input_validation("string")
    assert not input_validation([1, 2, 3])
