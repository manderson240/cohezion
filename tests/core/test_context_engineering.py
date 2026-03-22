import unittest

from bmad.core.context_engineering import ContextEngineeringInfrastructure



class TestContextEngineeringInfrastructure(unittest.TestCase):
    def setUp(self):
        self.cei = ContextEngineeringInfrastructure()

    def test_register_and_list_tools(self):
        self.assertEqual(self.cei.list_tools(), [])
        self.cei.register_tool("test_tool", lambda x: x * 2)
        self.assertEqual(self.cei.list_tools(), ["test_tool"])

    def test_execute_tool(self):
        self.cei.register_tool("test_tool", lambda x: x * 2)
        self.assertEqual(self.cei.execute_tool("test_tool", x=5), 10)

    def test_execute_tool_not_found(self):
        with self.assertRaises(ValueError):
            self.cei.execute_tool("non_existent_tool")


if __name__ == "__main__":
    unittest.main()
