# zwave-js-helper

A script that communicates with [Z-Wave JS](https://github.com/zwave-js) to enforce settings of Z-Wave devices. Designed to work with Home Assistant to remove the drudge of configuring multiple switches/sensors/etc to have identical settings.

## Installation:

* Clone the git repository OR download the release file
* `python3 setup.py install`
* `zwave-js-helper.py --settings enforce.yaml`

### Arguments:
```
./zwave-js-helper.py --help
usage: zwave-js-helper.py [-h] [-E] [-s ENFORCE_FILE] [-d] [-H HOST] [-p PORT] [-D]

Set Z-Wave values across multiple nodes

options:
  -h, --help            show this help message and exit
  -E, --enforce         By default, no Z-Wave values are changed. 
                        Set this flag to actively set values.
  -s ENFORCE_FILE, --settings ENFORCE_FILE
                        YAML settings file with settings to enforce (default: first of:
                        ['~/.config/zwave-js-helper/enforce.yaml', './enforce.yaml'])
  -d, --debug           Print the websocket messages
  -H HOST, --host HOST  zwave-js hostname to connect to (default: 127.0.0.1)
  -p PORT, --port PORT  zwave-js port to connect to (default: 3000)
  -D, --dump            Dump Z-Wave devices to zwave-js-helper-nodes/NN.json

NOTE: dry-run is default behavior. To actually set values pass `--enforce'.
```

The settings file (`enforce.yaml`) can be in the `$XDG_CONFIG_HOME` directory (usually `~/.config/zwave-js-helper/` on Linux) or the current directory.

## Configuration

The `enforce.yaml` file contains a list of values to enforce, and node properties that must match:
```
- title: A meaningful title that will be printed

  enforce:
    - label: The name/label of the Z-Wave property 
      value: The Value to enforce

  match:
    label: LZW31-SN # All Inovelli Red Series Dimmers
    name: # A list of specific node names this applies to
      - Laundry Room Dimmer
      - Mrs Bathroom Dimmer
```

Technically, the keys in `match:` can be anything at the top level definition of the node, or anything in `deviceConfig`. In practice, the most useful keys are `label:` and `name:`. Sometime `firmwareVersion:` is useful to restrict settings to only a specific firmware (or list of firmware) version(s).

Everything under `match:` is an AND, but lists within keys are ORs. in the above example, only the named nodes will be checked, AND they must be of type LZW31-SN.

### Configuration Example
This example sets the Auto-off property (with various caps and punctuation variations) to 1200 seconds for the named nodes.
```
- title: Auto Off Timer
  # Auto-off after 20 minutes, for final inspection.

  enforce:
    - label: Auto Off Timer
      value: 1200

    - label: Auto-Off Timer
      value: 1200

    - label: Auto-off Timer
      value: 1200

  match:
    name:
      - Laundry Room Dimmer
      - Mrs Bathroom Dimmer
      - Oddball Bathroom Dimmer
      - Guest Bathroom Dimmer
      - Garage Lights Switch

```

See the included `enforce.yaml` for more examples.
