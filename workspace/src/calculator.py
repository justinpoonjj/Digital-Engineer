def add(a, b):
    return a + b

def subtract(a, b):
    return a - b

def multiply(a, b):
    return a * b

def divide(a, b):
    if not input_validation(a, b):
        raise TypeError("Inputs must be integers or floats")
    return a / b

def power(a, b):
    return a ** b

def input_validation(a, b):
    return isinstance(a, (int, float)) and isinstance(b, (int, float))
