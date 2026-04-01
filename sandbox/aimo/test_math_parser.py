import unittest

from math_parser import MathParser


class TestMathParser(unittest.TestCase):
    def setUp(self):
        self.parser = MathParser()

    def test_domain_detection_algebra(self):
        problem = "Solve the equation $x^2 - 5x + 6 = 0$ for $x$."
        state = self.parser.parse(problem)
        self.assertGreater(state.algebra, 0.0)
        self.assertEqual(state.number_theory, 0.0)

    def test_domain_detection_number_theory(self):
        problem = "Find the number of distinct positive divisors of $n = 3^3 \cdot 11^3$."
        state = self.parser.parse(problem)
        self.assertGreater(state.number_theory, 0.0)

    def test_complexity_metric(self):
        simple = "What is $1+1$?"
        complex_prob = "Let $f(x) = \sum_{n=1}^{\infty} \frac{x^n}{n^2}$. Find $f'(1)$."
        s1 = self.parser.parse(simple)
        s2 = self.parser.parse(complex_prob)
        self.assertGreater(s2.structural_depth, s1.structural_depth)

if __name__ == "__main__":
    unittest.main()
