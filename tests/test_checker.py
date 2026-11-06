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

    def test_log_is_known(self):
        self.assertEqual(check('log("started")\n'), [])

    def test_local_str8_is_rejected(self):
        code = ('func str8 f() {\n'
                '  str8 s = "x"\n'
                '  s = s + "y"\n'
                '  return s\n'
                '}\n')
        errors = check(code)
        self.assertTrue(any("local str8" in m for _, m in errors))

    def test_techage_helpers_are_known(self):
        code = ('hold()\n'
                'release()\n'
                'dclr(1)\n'
                'dputs(1, 0, "x")\n'
                'printf("%s %d %d\\n", daytime$(0), time(), daytime())\n')
        self.assertEqual(check(code), [])


if __name__ == "__main__":
    unittest.main()
