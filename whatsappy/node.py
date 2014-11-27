from collections import MutableMapping

XML_ENT = {
    "&": "&amp;",
    "<": "&lt;",
    ">": "&gt;",
    '"': "&quot;"
}

class Node(MutableMapping):
    def __init__(self, tag, data=None, children=None, **kwargs):
        """
        Construct a new node. Any kwargs are assumed to be attributes, therefore
        the arguments are accessed trough 'args'.
        """

        self.name = tag
        self.data = data
        self.attributes = kwargs

        # Child nodes
        if children:
            if type(children) == list:
                self.children = children
            elif isinstance(children, Node):
                self.children = list(children)
            else:
                raise ValueError("Expected Node as child")
        else:
            self.children = []

    def __iter__(self):
        return iter(self.attributes)

    def __len__(self):
        return len(self.attributes)

    def __getitem__(self, key):
        return self.attributes[key]

    def __setitem__(self, key, value):
        self.attributes[key] = value

    def __delitem__(self, key):
        del self.attributes[key]

    def __contains__(self, key):
        return key in self.attributes

    def keys(self):
        return self.attributes.keys()

    def add(self, child):
        self.children.append(child)

    def remove(self, child):
        self.children.remove(child)

    def child(self, name):
        for child in self.children:
            if child.name == name:
                return child
        return None

    def has_child(self, name):
        return self.child(name) is not None

    def has_attribute(self, attribute):
        return attribute in self and self[attribute] is not None

    def escape(self, string):
        def escape_char(c):
            if c in XML_ENT:
                return XML_ENT[c]
            elif ord(c) < 0x20 or ord(c) >= 0x7f:
                return "&#x%02x;" % ord(c)
            else:
                return c

        if string is None:
            return "None"
        if not isinstance(string, basestring):
            raise TypeError("Expected str or unicode, got: %s" % type(string))
        return "".join(map(escape_char, string))

    def __str__(self):
        return self.to_xml()

    def to_xml(self, indent=0, level=0):
        prefix = (indent * level) * " "

        # Opening tag + attributes
        xml = "%s<%s" % (prefix, self.name)

        for attribute, value in self.attributes.iteritems():
            xml += " %s=\"%s\"" % (attribute, self.escape(value))

        xml += ">\n"

        # Data, with extra indent.
        if self.data:
            xml += "%s%s%s\n" % (prefix, indent * " ", self.escape(self.data))

        # Children
        for child in self.children:
            child = child.to_xml(indent=indent, level=level + 1)
            xml += "%s%s\n" % (prefix, child)

        # Closing tag
        xml += "%s</%s>" % (prefix, self.name)

        return xml

    def __repr__(self):
        return "<%s (%d)>" % (self.name, len(self.children))