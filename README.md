[![Codacy Badge](https://api.codacy.com/project/badge/Grade/3df5f854b1e44e65a1c3fc5331d4043f)](https://www.codacy.com/app/madrisan/pyxymon?utm_source=github.com&amp;utm_medium=referral&amp;utm_content=madrisan/pyxymon&amp;utm_campaign=Badge_Grade)
[![License](https://img.shields.io/badge/License-GPL--3.0-blue.svg)](https://spdx.org/licenses/GPL-3.0.html)

# PyXymon

PyXymon is a simple Python module that can help you write Xymon external scripts in Python.
PyXymon provides some methods for rendering the messages you want to display in the Xymon web page and for sending them to the Xymon server.
PyXymon reads the required informations from the Xymon environment variables, so you do not need to add any extra configuration file.

## Installation

Just copy the module `pyxymon.py` in the xymon `ext` directory.

## Usage

Create a script `yourcheck.py` using the following schema:

```
#!/usr/bin/python

import os
import sys
import pyxymon as pymon

check_name = 'yourcheck'
check_version = (os.path.basename(__file__), '1')

def run_check():
    '''
    Check the status of whatever you want...
    '''
    xymon = pymon.XymonClient(check_name)

    # do your logic...
    # you can set the criticity of the final xymon message by using:
    #    xymon.set_color(xymon.STATUS_WARNING)
    # or
    #    xymon.set_color(xymon.STATUS_CRITICAL)
    # The default criticity is 'xymon.COLOR_OK' 
    
    xymon.title('Title in the xymon check page')
    xymon.section('Section Title',
                  'Text containing the lines you want to display')
    # You can add here other sections, if required.
    xymon.footer(check_version)
    xymon.send()

def main():
    run_check()

if __name__ == '__main__':
    main()
    sys.exit(0)
```

Configure your extention module in the file `$XYMONCLIENTHOME/etc/xymonclient.cfg`.

```
[yourcheck]
        ENVFILE $XYMONCLIENTHOME/etc/xymonclient.cfg
        CMD $XYMONCLIENTHOME/ext/yourcheck.py
        LOGFILE $XYMONCLIENTLOGS/yourcheck.log
        INTERVAL 10m
```

You can find a full example [here](example/bb-pacemaker.py).

## Note

If you need to run your Python check with root privileges, just prefix the `CMD` directive in `xymonclient.cfg`
with the `sudo` command:  

        CMD sudo $XYMONCLIENTHOME/ext/yourcheck.py

By default *sudo* does not preserve the environment variables exported by Xymon.
To preserve the variables required by *PyXymon*, add the following lines to the *sudo* configuration:

```
 Defaults env_keep:xymon += "XYMSRV"
 Defaults env_keep:xymon += "XYMONDPORT"
 Defaults env_keep:xymon += "MACHINE"
```
