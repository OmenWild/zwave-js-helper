#! /usr/bin/env -S python3 -u

"""zwave-js-helper.py: enforce Z-Wave device properties."""

__author__      = "Omen Wild"
__copyright__   = "Copyright 2022, Omen Wild"
__license__ = "GPLv2"
__version__ = "1.0"

from collections import namedtuple
from pathlib import Path

import argparse
import json
import pprint
import sys
import websocket
import xdg.BaseDirectory
import yaml

PROGRAM = Path(sys.argv[0]).stem

class ZWJSHelper():
    # A structured way to store the changes needed for a node.
    Change = namedtuple("Change", ['s', 'nodeId', 'property', 'commandClass', 'current', 'to'])

    def __init__(self, args):
        self.messageId = 0
        self._pp = pprint.PrettyPrinter(compact=False, sort_dicts=True)

        self.debug = args.debug
        self.dry_run = args.dry_run
        self.enforce_file = args.enforce_file

        self.url = f"ws://{args.host}:{args.port}"

        try:
            self.ws = websocket.create_connection(self.url)
        except ConnectionRefusedError:
            print(f"Unable to connect to `{self.url}', do you need to pass a different host (--host=other-ip)?")
            sys.exit(1)
        except websocket._exceptions.WebSocketAddressException:
            print(f"Unable to resolve host in URL `{self.url}'. Typo? Or do you need to use the IP?")
            sys.exit(1)

        # Receive the header
        i = self.recv()

        # Set the schema level this program was written to use
        i = self.send({
            "command": "set_api_schema",
            "schemaVersion": 24
            })
        i = self.recv()

        # Load values to enforce from the yaml file
        self.load_enforce()

        # Load the nodes from zwave-js
        self.load_nodes()

        if args.dump:
            self.dump()

        # Check, and if necessary, enforce settings
        self.check_all_nodes()


    def dump(self):
        dir = Path(f"{PROGRAM}-nodes")
        print(f"Dumping all node data to: {dir}/")
        if not dir.exists():
            dir.mkdir()

        for k in sorted(self.nodes.keys()):
            n = self.nodes[k]
            p = dir / Path(f"{k}.json")
            p.write_text(json.dumps(n, indent=4, sort_keys=True))


    def pp(self, label, value):
        print(label)
        self._pp.pprint(value)
        print()


    def check_match(self, enforce, node):
        # Check if a specific node matches the match: section of an entry.

        for k, v in enforce['match'].items():
            if k == 'firmwareVersion':
                # Special handling for firmwareVersion as it is a String in the JSON.
                if isinstance(v, list):
                    v = [str(x) for x in v]
                else:
                    v = str(v)

            if isinstance(v, str):
                if k in node and node[k] != v:
                    return False
                if k in node['deviceConfig'] and node['deviceConfig'][k] != v:
                    return False
            elif isinstance(v, list):
                if k in node and node[k] not in v:
                    return False
                if k in node['deviceConfig'] and node['deviceConfig'][k] not in v and not isinstance(node['deviceConfig'][k], dict):
                    return False

        return True


    def check_all_nodes(self):
        # Check all nodes to see if they need update, and set them if necessary.
        print()
        
        changes_applied = 0
        for k in sorted(self.nodes.keys()):
            node = self.nodes[k]
            for enforce in self.enforce_values:
                if self.check_match(enforce, node):
                    changes = self.check_node(enforce, node)
                    if changes:
                        print(f"{node['name']} ({node['nodeId']}):")
                        for c in changes:
                            changes_applied += 1
                            if self.dry_run:
                                print(f"  Dry run: {c.s}")
                            else:
                                self.set_value(c)
                                print("  ", c.s)
                        print()

        print()
        if changes_applied == 0:
            print("Checked all nodes, no values need changing.")
        else:
            if self.dry_run:
                print(f"Dry run: {changes_applied} updates need to be applied.")
            else:
                print(f"{changes_applied} applied.")



    def check_node(self, enforce, node):
        # Check if the values for a specific, already matched node, need updates.

        changes = []
        for e in enforce['enforce']:
            for value in node['values']:
                if 'label' in value['metadata'] and value['metadata']['label'] == e['label']:
                    if value['value'] != e['value']:
                        if not value['metadata']['writeable']:
                            raise ValueError(f"Property `{e['label']}' is read-only for node: {node['name']}")

                        s = f"{enforce['title']} ({e['label']}): {value['value']} => {e['value']}"
                        c = ZWJSHelper.Change(s, node['nodeId'], value['property'], value['commandClass'], value['value'], e['value'])
                        changes.append(c)

        return changes


    def set_value(self, change):
        c = {
            'command': "node.set_value",
            'nodeId': change.nodeId,
            'valueId': {
                'commandClass': change.commandClass,
                'property': change.property,
            },
            'value': change.to,
        }

        self.send(c)


    def load_nodes(self):
        self.nodes = {}

        print("Loading nodes, ", end='')
        i = self.send({
            "command": "start_listening"
        })
        j = self.recv()
        nodes = j['result']['state']['nodes']
        for node in nodes:
            self.nodes[node['name']] = node

        print(f"done, {len(nodes)} nodes loaded.")


    def load_enforce(self):
        self.enforce_values = []

        print(f"Loading enforcement values from: {self.enforce_file}, ", end='')
        f = open(self.enforce_file, 'r')
        data = yaml.load(f, Loader=yaml.FullLoader)

        # Do some sanity checking on the config as it is loaded.
        for item in data:
            if not 'match' in item:
                raise ValueError("For your sanity, a `match' section is required in every section, but you may leave it blank.", item['title'])

            if not 'enforce' in item:
                raise ValueError("Every entry requires an `enforce:' list of items to set.", item['title'])

            self.enforce_values.append(item)

        print(f"done. Loaded {len(self.enforce_values)} items.")

        if self.debug:
            print("# ENFORCE")
            print(json.dumps(self.enforce_values, indent=4))


    def recv(self):
        j = json.loads(self.ws.recv())
        if self.debug:
            print("# <<<")
            print(json.dumps(j, indent=4))
            print()

        return j


    def send(self, msg):
        self.messageId += 1
        msg['messageId'] = f"{self.messageId}"

        if self.debug:
            print("# >>>")
            print(json.dumps(msg, indent=4))
            print()

        self.ws.send(json.dumps(msg))
        return self.messageId


if __name__ == "__main__":
    config_dir = Path(xdg.BaseDirectory.save_config_path(PROGRAM))

    parser = argparse.ArgumentParser(formatter_class=argparse.RawDescriptionHelpFormatter,
                                     description="Set Z-Wave values across multiple nodes",
                                     epilog="NOTE: dry-run is default behavior. To actually set values pass `--enforce'."
                                     )

    parser.add_argument("-E", "--enforce", action="store_false",
                        dest="dry_run",
                        help="By default, no Z-Wave values are changed. Set this flag to actively set values.")

    parser.add_argument("-s", "--settings", type=str,
                        default=[f"{config_dir}/enforce.yaml", './enforce.yaml'],
                        dest="enforce_file",
                        help="YAML settings file with settings to enforce (default: %(default)s)")

    parser.add_argument("-d", "--debug", action="store_true",
                        dest="debug",
                        help="Print the websocket messages")

    parser.add_argument("-H", "--host", type=str, default='127.0.0.1',
                        help="zwave-js hostname to connect to (default: %(default)s)")

    parser.add_argument("-p", "--port", type=int, default=3000,
                        help="zwave-js port to connect to (default: %(default)s)")

    parser.add_argument("-D", "--dump", action="store_true",
                        dest="dump",
                        help=f"Dump Z-Wave devices to {PROGRAM}-nodes/NN.json")


    args = parser.parse_args()

    if isinstance(args.enforce_file, list):
        for f in args.enforce_file:
            p = Path(f)
            if p.exists():
                args.enforce_file = p
    elif isinstance(args.enforce_file, str):
        p = Path(args.enforce_file)
        if p.exists():
            args.enforce_file = p

    if not isinstance(args.enforce_file, Path):
        print(f"Unable to find an enforce.yaml file in either {config_dir} or the current directory.")
        sys.exit(1)

    if args.dry_run:
        print("NOTE: in dry-run mode, call with `--enforce' to set values.\n")

    ZWJSHelper(args)
