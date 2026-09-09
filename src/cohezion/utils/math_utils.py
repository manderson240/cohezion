"""
Mathematical utility functions for Cohezion framework.
"""

def factorial(n: int) -> int:
    """
    Compute the factorial of a non-negative integer.
    
    Args:
        n: A non-negative integer
        
    Returns:
        The factorial of n (n!)
        
    Raises:
        ValueError: If n is negative
        TypeError: If n is not an integer
        
    Examples:
        >>> factorial(5)
        120
        >>> factorial(0)
        1
    """
    # Input validation
    if not isinstance(n, int):
        raise TypeError("Factorial is only defined for integers")
    if n < 0:
        raise ValueError("Factorial is not defined for negative numbers")

    # Base cases
    if n == 0 or n == 1:
        return 1

    # Compute factorial iteratively to avoid recursion limits
    result = 1
    for i in range(2, n + 1):
        result *= i

    return result
