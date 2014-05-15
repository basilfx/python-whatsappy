# python-whatsappy
A Python API for connecting with the chat protocol.

## Dependencies
The Client uses the [pbkdf2 library](https://www.dlitz.net/software/python-pbkdf2/)
written by Dwayne C. Litzenberger, which you can install using `pip install pbkdf2`.

## Usage
The API is callback driven and very easy to use. See below for a simple example.

```
import whatsappy

# Connecting
client = whatsappy.Client(number=<number>, secret=<secret>, nickname=<nickname>)
client.login()

# Callback
def on_message(node):
    message = node.child("body").data
    sender = node["from"]

    # Print response to terminal
    print "%s: %s" % (sender, message)

    # Reply
    client.message(receiver, message)

# Register callback
client.register_callbacks(
    TextMessageCallback(on_message, single=True, group=True, offline=True)
)
```

One can examining of raw messages by turning on debug. Other messages are logged
via Python's logging functionality.

```
client.debug = True
```

This module does not provide any method to generate a login secret. You should
provide it yourself, e.g. intercept it from your phone.

## License
Released under the MIT License

Copyright (C) 2012 Paul Hooijenga (Original author)
Copyright (C) 2014 Bas Stottelaar

Permission is hereby granted, free of charge, to any person obtaining a copy of
this software and associated documentation files (the "Software"), to deal in
the Software without restriction, including without limitation the rights to
use, copy, modify, merge, publish, distribute, sublicense, and/or sell copies
of the Software, and to permit persons to whom the Software is furnished to do
so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS
FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR
COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER
IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN
CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

## Disclaimer
WhatsApp is a registered trademark of WhatsApp Inc registered in the U.S. and
other countries. This project is an independent work and has not been
authorized, sponsored, or otherwise approved by Whatsapp Inc.