import os

tokenfile = os.path.join(os.path.dirname(__file__), "tokens")
with open(tokenfile, "r") as fp:
    TOKENS = [line.strip() for line in fp]

def str2tok(string):
    """Convert a string to a token. Returns None if the string is not a token."""

    return TOKENS.index(string) if string in TOKENS else None

def tok2str(index):
    """Convert a token to a string. Returns None if the token is not valid."""

    return TOKENS[index] if 0 <= index < len(TOKENS) else None

if __name__ == "__main__":
    import sys

    for arg in sys.argv[1:]:
        if arg.startswith("0x"):
            print arg, tok2str(int(arg, 16))
        else:
            print arg, str2tok(arg)
