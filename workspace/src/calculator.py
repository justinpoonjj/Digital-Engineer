def add(a, b):
    return a + b

def subtract(a, b):
    return a - b

def multiply(a, b):
    return a * b

def divide(a, b):
    if not input_validation(a) or not input_validation(b):
        raise TypeError("Inputs must be integers or floats")
    if b == 0:
        raise ValueError("Cannot divide by zero")
    return a / b

def power(a, b):
    return a ** b

def input_validation(x):
    return isinstance(x, (int, float))
