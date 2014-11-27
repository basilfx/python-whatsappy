from whatsappy import Node

import unittest

class NodeTest(unittest.TestCase):
    def test_init(self):
        """
        Test some variants of the Node __init__ method
        """

        node = Node("name", "data")
        self.assertEqual("name", node.name)
        self.assertEqual("data", node.data)

        node = Node("name", attr1="value1", attr2="value2")
        self.assertEqual(dict(attr1="value1", attr2="value2"), node.attributes)

    def test_to_xml(self):
        """
        Test if serializing to XML works
        """

        node = Node("name")
        self.assertEqual("<name></name>", node.to_xml())

        node = Node("name", "data")
        self.assertEqual("<name>\n    data\n</name>", node.to_xml(indent=4))

        node = Node("name", children=[Node("child1"), Node("child2")])
        xml = ("<name>\n" +
               "    <child1></child1>\n" +
               "    <child2></child2>\n" +
               "</name>")
        self.assertEqual(xml, node.to_xml(indent=4))

    def test_has_child(self):
        """
        Test has child methods.
        """

        node = Node("name", children=[Node("child1"), Node("child2")])

        self.assertTrue(node.has_child("child1"))
        self.assertTrue(node.has_child("child2"))

    def test_has_attribute(self):
        """
        Test has attribute methods.
        """

        node = Node("name", attr1="attribute", attr2=None)

        self.assertTrue(node.has_attribute("attr1"))
        self.assertFalse(node.has_attribute("attr2"))

    def test_dict(self):
        """
        Test some of the dictionary interface
        """

        node = Node("name")
        node["attr1"] = "value1"

        self.assertTrue("attr1" in node.attributes)
        self.assertTrue("attr1" in node)
        self.assertEqual(1, len(node))

        for key in node: # Test iterator
            self.assertEqual("attr1", key)