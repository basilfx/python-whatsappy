from collections import MutableMapping

XML_ENT = {
    "&": "&amp;",
    "<": "&lt;",
    ">": "&gt;",
    '"': "&quot;"
}

class Node(MutableMapping):
    def __init__(self, name, data=None, children=None, **attributes):
        self.name = name
        self.data = data
        self.children = children if children else []
        self.attributes = attributes

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

    def child(self, name):
        for child in self.children:
            if child.name == name:
                return child
        return None

    def has_child(self, name):
        return self.child(name) != None

    def toxml(self, indent=""):
        xml = indent + "<" + self.name
        for name in sorted(self.attributes.keys()):
            xml += " " + str(name) + "=\"" + self.escape(self.attributes[name]) + "\""
        xml += ">"

        if self.data:
            xml += self.escape(self.data)

        if self.children:
            xml += "\n"
            for child in self.children:
                xml += child.toxml(indent + "  ") + "\n"
            xml += indent

        xml += "</" + self.name + ">"
        return xml

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
        return self.toxml()

    def __repr__(self):
        return "<%s (%d)>" % (self.name, len(self.children))