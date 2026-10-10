import unittest

from nanoc_client.checker import check


class TestChecker(unittest.TestCase):
    def test_ok(self):
        code = ('int32 c = 0\n'
                'while (1) {\n'
                '  c = c + 1\n'
                '  printf("%d\\n", c)\n'
                '  sleep(1000)\n'
                '}\n')
        self.assertEqual(check(code), [])

    def test_unknown_function(self):
        errors = check('prinf("x")\n')
        self.assertTrue(any("unknown function" in m for _, m in errors))
        self.assertEqual(errors[0][0], 1)

    def test_undeclared_variable(self):
        errors = check('int32 a = 0\na = b + 1\n')
        self.assertTrue(any("undeclared" in m for _, m in errors))
        self.assertEqual([ln for ln, m in errors if "undeclared" in m], [2])

    def test_unbalanced(self):
        errors = check('int32 a = 0\nwhile (1) {\n  a = a + 1\n')
        self.assertTrue(any("unclosed" in m for _, m in errors))

    def test_assignment_declares(self):
        self.assertEqual(check('x = 5\nprintf("%d\\n", x)\n'), [])


if __name__ == "__main__":
    unittest.main()
