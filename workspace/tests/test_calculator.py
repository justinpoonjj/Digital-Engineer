import pytest

from calculator import add, divide, input_validation, multiply, power, subtract


def test_add():
    assert add(1, 2) == 3
    assert add(-1, 1) == 0
    assert add(-1, -1) == -2

def test_subtract():
    assert subtract(10, 5) == 5
    assert subtract(0, 0) == 0
    assert subtract(-1, -1) == 0

def test_multiply():
    assert multiply(3, 4) == 12
    assert multiply(-1, 1) == -1
    assert multiply(-1, -1) == 1

def test_divide():
    with pytest.raises(TypeError):
        divide("a", 2)
    with pytest.raises(TypeError):
        divide(2, "b")
    with pytest.raises(ZeroDivisionError):
        divide(5, 0)
    assert divide(8, 4) == 2
    assert divide(-1, 1) == -1
    assert divide(-1, -1) == 1

def test_power():
    assert power(2, 3) == 8
    assert power(5, 0) == 1
    assert power(2, -1) == 0.5

def test_input_validation():
    assert input_validation(1, 2)
    assert not input_validation("a", 2)
    assert not input_validation(2, "b")
