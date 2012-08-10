# vim: ts=4 et sw=4 sts=4

import os
import sys
import rci
import time
import socket
import telnetlib
import subprocess

class Node:

    def __init__(self):
        self.message_count = 0

    def configure(self, configuration):

        for a in Node.get_required_attributes():
            if a not in configuration.keys():
                raise KeyError, "Configuration must include key '%s'"%(a,)
        id = configuration["id"]

        try:
            self.id = int(id)
        except ValueError:
            raise ValueError, "ID must be an integer"

    def install(self):
        pass

    def is_install_success(self):
        return True

    def message_counter(self, line):
        """Simple callback function for the managed subprocess module that
        counts the messages that were received by the serial forwarder.
        """
        self.message_count += 1

    def reset_message_counter(self):
        self.message_count = 0

    def get_message_counter(self):
        return self.message_count

    def get_required_attributes():
        return ["id"]
    get_required_attributes = staticmethod(get_required_attributes)

from string import Template

class TelosMote(Node):

    def __init__(self):
        Node.__init__(self)

    def configure(self, configuration):
        Node.configure(self, configuration)

        for a in TelosMote.get_required_attributes():
            if a not in configuration.keys():
                raise KeyError, "Configuration must include key '%s'"%(a,)
        serialid = configuration["serialid"]
        self.serialid = serialid
        installCmd = configuration["installCmd"]

        proc = subprocess.Popen("motelist | grep %s"%(serialid,), shell=True,
                stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        proc.wait()

        s = proc.stdout.readlines()
        if len(s) != 1:
            raise KeyError, "SerialID %s not found!"%serialid

        self.serial = s[0].split()[1]
        if not os.path.exists(self.serial):
            raise ValueError, "ERROR: Serial port %s does not exist\n"%(self.serial,)

        template = Template(installCmd)
        self.installCmd = template.substitute(serial = self.serial, id=self.id)

    def install(self):

        self.installSuccess = False
        proc = subprocess.Popen(self.installCmd, shell=True, stdout=subprocess.PIPE,
                stderr=subprocess.PIPE)
        proc.wait()

        if proc.returncode != None:
            if proc.returncode == 0:
                self.installSuccess = True
            else:
                # compilation failed
                sys.stderr.write(
"""ERROR: Compilation Failed. Output from command "%s":\n"""%(self.installCmd,))
                sys.stderr.write("".join(proc.stdout.readlines()))
                sys.stderr.write("\n")
                sys.stderr.write("".join(proc.stderr.readlines()))
                self.installSuccess = False
        else:
            # something went wrong!
            self.installSuccess =  False

    def reset(self):
        """ Reset the specified telos mote using tos-bsl. """
        proc = subprocess.Popen("tos-bsl --telosb -c %s -r"%(self.serial), shell=True,
                stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        proc.wait()

    def is_install_success(self):
        return self.installSuccess

    def get_required_attributes():
        return Node.get_required_attributes() + ["serialid", "installCmd"]
    get_required_attributes = staticmethod(get_required_attributes)

class QuantoTestbedMote(Node):

    # The better way might have been to move this configuration information to
    # an external file, but it should be a static property of all Quanto motes,
    # and thus an inherent property of being a Quanto.

    DEFAULT_INSTALL_COMMAND = "make epic reinstall,$id digi bsl,$serial"
    DEFAULT_TIMEOFFSET = 0
    NODES = {
            "rd":"00:40:9d:3d:6c:31",
            "re":"00:40:9d:3d:69:ed",
            "rg":"00:40:9d:3d:6c:21",
            "rk":"00:40:9d:3d:6c:16",
            "rl":"00:40:9d:3d:6a:29",
            "rm":"00:40:9d:3d:6a:d5",
            "rs":"00:40:9d:3d:6a:d1",
            "rv":"00:40:9d:3d:6c:20",
            "rw":"00:40:9d:38:24:90",
            "sb":"00:40:9d:3d:6b:0a"
    }

    def __init__(self):
        Node.__init__(self)
        self.installSuccess = False
        self.frequencies = {}
        self.statePower = {}
        self.alwaysOffStates = []
        self.alwaysOnStates = []

    # Propogates KeyError on failure
    def get_node_info_by_name(self, name):
        # I believe the Digi namespace is solid?
        serial = "/dev/tty" + name + "00"

        # Will raise KeyError if unknown node
        mac = self.NODES[name]
        host = mac.replace(":", "-") + ".eecs.umich.edu"

        # Generate a consistent, unique id as a courtesy
        k = self.NODES.keys()
        k.sort()
        id = k.index(name) + 1

        return id, host, serial

    def _verify_config(self, host, serial, installCmd):
        # check if we can telnet to the IP
        self.host = host

        try:
            t = telnetlib.Telnet()
            t.open(host)
            t.read_until("login: ", timeout=1)
            t.close()
        except socket.error:
            raise ValueError, "ERROR: Could not connect to node at %s\n"%(self.host,)

        self.serial = serial
        if not os.path.exists(self.serial):
            raise ValueError, "ERROR: Serial port %s does not exist\n"%(self.serial,)

        template = Template(installCmd)
        self.installCmd = template.substitute(serial = self.serial, id=self.id)

        # add the RCI interface
        self.rci = rci.RCI(self.host)

    def configure_ex(self, key, config):
        if config.has_option(key, "name"):
            try:
                name = config.get(key, "name")
                id, host, serial = self.get_node_info_by_name(name)

            except KeyError:
                print "WARN: Error parsing node with name ", name
                print "      Failing over to default configure path"
                print
                print "You may need to add this node to the NODES array in the"
                print "QuantoTestbedMote class if it is a new node"
                raise AttributeError

            # Allow override from config file
            host = config.get(key,"ip") if config.has_option(key,"ip") else host
            serial = config.get(key,"serial") if config.has_option(key,"serial") else serial
            installCmd = config.get(key,"installCmd") if config.has_option(key,"installCmd") else self.DEFAULT_INSTALL_COMMAND
            self.timeoffset = config.get(key,"timeoffset") if config.has_option(key,"timeoffset") else self.DEFAULT_TIMEOFFSET

            # Set a unique id as a courtesy as it is common to all Node types
            if not config.has_option(key,"id"):
                config.set(key, "id", id)

            self.id = config.get(key, "id")

            self._verify_config(host, serial, installCmd)
        else:
            # Raising AttributeError falls back to standard configure path
            raise AttributeError

    def configure(self, configuration):
        Node.configure(self, configuration)

        for a in QuantoTestbedMote.get_required_attributes():
            if a not in configuration.keys():
                raise KeyError, "Configuration must include key '%s'"%(a,)
        # rename to more appropriate term 'host' as ip or hostname both work
        host = configuration["ip"]
        serial = configuration["serial"]
        installCmd = configuration["installCmd"]
        self.timeoffset = int(configuration["timeoffset"])

        self._verify_config(host, serial, installCmd)

    def install(self):

        # enable RTS for serial communication
        self.rci.set_gpio_mode(rci.RTS, rci.SERIAL)

        proc = subprocess.Popen(self.installCmd, shell=True, stdout=subprocess.PIPE,
                stderr=subprocess.PIPE)
        proc.wait()

        if proc.returncode != None:
            if proc.returncode == 0:
                self.installSuccess = True
            else:
                # compilation failed
                sys.stderr.write(
"""ERROR: Compilation Failed. Output from command "%s":\n"""%(self.installCmd,))
                sys.stderr.write("".join(proc.stdout.readlines()))
                sys.stderr.write("\n")
                sys.stderr.write("".join(proc.stderr.readlines()))
                self.installSuccess = False
        else:
            # something went wrong!
            self.installSuccess =  False

        # revert RTS line to HIGH
        self.rci.set_gpio_high(rci.RTS)

    def is_install_success(self):
        return self.installSuccess

    def push_usr(self):
        self.rci.set_gpio_low(rci.DSR)

    def release_usr(self):
        self.rci.set_gpio_high(rci.DSR)

    def reset(self):
        self.rci.set_gpio_low(rci.RTS)
        self.rci.set_gpio_high(rci.RTS)

    def stop(self):
        self.rci.set_gpio_low(rci.RTS)

    def start(self):
        self.rci.set_gpio_high(rci.RTS)

    def programming_mode(self):
        """ put the node into programming mode by setting the RTS gpio line to
        serial mode.
        """
        self.rci.set_gpio_mode(rci.RTS, rci.SERIAL)

    def serial_mode(self):
        """ put the node into serial mode by setting the RTS line to gpio mode
        high.
        """
        self.rci.set_gpio_high(rci.RTS)

    def calibrate(self, frequencies, time=time.localtime()):
        """ This method aways a dictionary as parameter. Each entry in the
        dictionary has a numeric key, and the value is again a digtionary with
        the keys:
         'res':    string representation of the resistor value
         'freq':   iCount frequency measured for this resistor
         'E':      the energy quanta per iCount for a given frequency

         The key of the frequencies dictionary is the numerical representation
         of the calibration resistor. This way, the frequencies can easily be
         sorted by increasing, or decreasing resistor value.
        """

        self.frequencies = frequencies

    def get_energy(self, icount, time):
        """
        This method calculates the consumed power for a specific number of
        icounts and the duration time. It uses the values from the calibration
        or else returns -1.

        The returned value is in milli Joul.
        """

        if len(self.frequencies) == 0:
            return -1

        if time <= 0:
            return 0.0
        frequency = icount / float(time)

        # search for the closest frequency in our calibration table
        keys = self.frequencies.keys()
        # sort by increasing resistor values (decreasing frequencies)
        keys.sort()
        lastRes = -1
        for res in keys:
            if frequency <= self.frequencies[res]['freq']:
                lastRes = res
                continue
            else:
                break
        if res == keys[-1]:
            # the given frequency is below our highest frequency measurement.
            # Thus, we have to go with its value.
            return icount * self.frequencies[res]['E']
        if res == keys[0]:
            # the given frequency is above our lowest frequency measurement.
            # Thus, we have to go with its value.
            return icount * self.frequencies[res]['E']

        # interpolate between the two calibration frequencies
        df = self.frequencies[lastRes]['freq'] - self.frequencies[res]['freq']
        dE = self.frequencies[lastRes]['E'] - self.frequencies[res]['E']

        return icount * (
                (frequency - self.frequencies[res]['freq']) / df * dE
                + self.frequencies[res]['E'])

    def get_power(self, icount, time):
        """
        This will calculate the average power consumed during time. The
        returned value is in milli Watt.
        """

        if time <= 0:
            return 0.0

        return self.get_energy(icount, time) / float(time)

    def get_current(self, icount, time):
        return self.get_power(icount, time) / 3.3

    def get_required_attributes():
        return Node.get_required_attributes() + ["ip", "serial", "installCmd",
                "timeoffset"]
    get_required_attributes = staticmethod(get_required_attributes)
