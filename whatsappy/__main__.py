from argparse import ArgumentParser
from datetime import date, timedelta

from whatsappy.client import Client

import sys, base64

num_args = { "interactive": 0, "login": 0, "lastseen": 1, "message": (1, 2), "image": 2, "location": 3 }
commands = num_args.keys()

parser = ArgumentParser(prog="python -m whatsappy", description="Python WhatsApp Client")
parser.add_argument("command", help="command to perform", nargs="?", choices=commands, default=commands[0])
parser.add_argument("argument", help="command-specific arguments",nargs="*")
parser.add_argument("-v", "--verbose", help="increase output verbosity", action="store_true")
parser.add_argument("-d", "--debug", help="display debug output", action="store_true")

parser.add_argument("--number", help="your phone number")
parser.add_argument("--secret", help="your phone's imei or mac address")

args = parser.parse_args()

command = args.command
arguments = args.argument
nargs = len(arguments)
enargs = num_args[command]

if isinstance(enargs, tuple):
    minargs, maxargs = enargs
    if nargs < minargs:
        parser.error("%s takes at least %d arguments, %d specified" % (command, minargs, nargs))
    elif nargs > maxargs:
        parser.error("%s takes at most %d arguments, %d specified" % (command, maxargs, nargs))
elif nargs != enargs:
    parser.error("%s takes %d arguments, %d specified" % (command, enargs, nargs))

if not args.number or not args.secret:
    if command != "interactive":
        parser.error("--number and --secret are required when not running in interactive mode")

    if not args.number:
        print >>sys.stderr, "Please enter your phone number\n>",
        ars.number = raw_input().strip()
    if not args.secret:
        print >>sys.stderr, "Please enter your phone's MAC (iPhone) or IMEI (Android / BlackBerry)\n>",
        ars.secret = raw_input().strip()

if args.debug:
    args.verbose = True

client = Client(args.number, base64.b64decode(args.secret))
client.debug = args.debug
client.login()

if args.verbose:
    print "Account Type:    %s" % client.account_info["kind"]
    print "Account Status:  %s" % client.account_info["status"]
    print "Account Created: %s" % date.fromtimestamp(int(client.account_info["creation"]))
    print "Account Expires: %s" % date.fromtimestamp(int(client.account_info["expiration"]))
    print

if command == "interactive":
    # It's still not interactive, but it shows what is happening
    while True:
        client.service_loop()
elif command == "lastseen":
    number = arguments[0]
    s = client.last_seen(number)
    delta = timedelta(seconds=s)
    print "Last Seen %s at %s (%d hours ago)" % (number, date.today() - delta, s / 3600)
elif command == "message":
    number = arguments[0]
    if len(arguments) > 1:
        text = arguments[1]
    else:
        print >>sys.stderr, "Please enter the message to send\n>",
        text = raw_input().strip()
    print client.message(number, text)

elif command == "location":
  number = arguments[0]
  lat, lng = float(arguments[1]), float(arguments[2])
  print client.location(number, lat, lng)

elif command == "image":
  number, image = arguments
  # TODO
  # print client.image(number, url, name, size, thumb)
