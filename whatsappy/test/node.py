import unittest

from ..node import Node

class NodeTest(unittest.TestCase):
    def test_ctor(self):
        """Test some variants of the Node __init__ method"""

        node = Node("name", "data")
        self.assertEqual("name", node.name)
        self.assertEqual("data", node.data)

        node = Node("name", attr1="value1", attr2="value2")
        self.assertEqual(dict(attr1="value1", attr2="value2"), node.attributes)

    def test_toxml(self):
        """Test if serializing to XML works"""

        node = Node("name")
        self.assertEqual("<name></name>", node.toxml())

        node = Node("name", "data")
        self.assertEqual("<name>data</name>", node.toxml())

        node = Node("name", children=[Node("child1"), Node("child2")])
        xml = ("<name>\n" +
               "  <child1></child1>\n" +
               "  <child2></child2>\n" +
               "</name>")
        self.assertEqual(xml, node.toxml())

    def test_dict(self):
        """Test some of the dictionary interface"""

        node = Node("name")
        node["attr1"] = "value1"

        self.assertTrue("attr1" in node.attributes)
        self.assertTrue("attr1" in node)
        self.assertEqual(1, len(node))
        for key in node: # Test iterator
            self.assertEqual("attr1", key)
