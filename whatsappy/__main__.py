from argparse import ArgumentParser

from .client import Client

commands = ["interactive", "login", "lastseen", "message", "query"]

parser = ArgumentParser(prog="python -m whatsappy", description="Python WhatsApp Client")
parser.add_argument("command", help="command to perform", nargs="?", choices=commands, default=commands[0])
parser.add_argument("-v", "--verbose", help="increase output verbosity", action="store_true")
parser.add_argument("-d", "--debug", help="display debug output", action="store_true")

parser.add_argument("--number", help="your phone number")
parser.add_argument("--secret", help="your phone's imei or mac address")

args = parser.parse_args()

if args.command != "interactive" and (not args.number or not args.secret):
    parser.error("--number and --secret are required when not running in interactive mode")

if args.debug:
    args.verbose = True

if args.command == "interactive":
    interactive(args)
else:
    client = Client(args.number, args.secret)
    client.debug = args.debug
    client.login()

    if args.verbose:
        from datetime import date
        print "Account Info"
        print "------------"
        print "Type:    %s" % client.account_info["kind"]
        print "Status:  %s" % client.account_info["status"]
        print "Created: %s" % date.fromtimestamp(int(client.account_info["creation"]))
        print "Expires: %s" % date.fromtimestamp(int(client.account_info["expiration"]))
        print

    # TODO: How do we get extra args from the commandline here?
    if args.command == "lastseen":
        pass # TODO
    elif args.command == "message":
        pass # TODO
    elif args.command == "query":
        pass # TODO
