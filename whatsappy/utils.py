import time

def dump_bytes(buf, prefix):
    output = []

    for i in xrange(0, len(buf), 16):
        hex_string = byte_string = ""

        for j in range(0, 16):
            if i + j < len(buf):
                b = ord(buf[i + j])
                hex_string  += "%02x " % b
                byte_string += buf[i + j] if 0x20 <= b < 0x7F else "."
            else:
                hex_string  += "   "

            if (j % 4) == 3:
                hex_string += " "

        output.append(prefix + hex_string + byte_string)
    return "\n".join(output)

def dump_xml(node, prefix):
    output = []

    # Prefix output
    for line in node.to_xml(indent=4).split("\n"):
        output.append(prefix + line)

    return "\n".join(output)

def timestamp():
    return str(int(time.time()))