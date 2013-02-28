# Copyright cozybit, Inc 2010-2012
# All rights reserved

import wtf.node as node
import sys; err = sys.stderr

class MeshBase(node.NodeBase):
    """
    Mesh STA

    This represents a platform-independent mesh STA that should be used by tests.

    Real Mesh STAs should extend this class and implement the actual AP functions.
    """

    def __init__(self, comm):
        """
        Create mesh STA with the supplied default configuration.
        """
        node.NodeBase.__init__(self, comm=comm)

class MeshConf():
    """
    Mesh STA configuration object

    Use this to set options for the MBSS; SSID, channel, etc.
    XXX: add support for authsae
    """

    def __init__(self, ssid, channel=1, htmode="", security=0, iface=None,
                 mesh_params=None, mcast_rate=None, mcast_route=None):
        if not iface:
            raise UninitializedError("need iface for mesh config")
        self.iface = iface
        self.ssid = ssid
        self.channel = channel
        self.htmode = htmode
        self.security = security
        self.mesh_params = mesh_params
        self.mcast_rate = mcast_rate
        self.mcast_route = mcast_route

class MeshSTA(node.LinuxNode, MeshBase):
    """
    mesh STA node
    """
    def __init__(self, comm, ifaces):
        node.LinuxNode.__init__(self, comm, ifaces)
        self.configs = []
        self.mccapipe = None

    def start(self):
        # XXX: self.stop() should work since we extend LinuxNode?? 
        node.LinuxNode.stop(self)

        for config in self.configs:
            #self.set_iftype("mesh")
            self._cmd_or_die("iw " + config.iface.name + " set type mp")
            #node.set_channel(self.config.channel)
            self._cmd_or_die("iw " + config.iface.name + " set channel " + str(config.channel) +
                             " " + config.htmode)
            # must be up for authsae or iw
            self._cmd_or_die("ifconfig " + config.iface.name + " up")
            if config.security:
                self.authsae_join(config)
            else:
                self.mesh_join(config)
        node.LinuxNode.start(self)

    def stop(self):
        for config in self.configs:
            if config.security:
                self.comm.send_cmd("start-stop-daemon --quiet --stop --exec meshd-nl80211")
            else:
                self.comm.send_cmd("iw " + config.iface.name + " mesh leave")
        self.mccatool_stop()
        node.LinuxNode.stop(self)

    def authsae_join(self, config):
        # This is the configuration template for the authsae config
        confpath="/tmp/authsae-%s.conf" % (config.iface.name)
        logpath="/tmp/authsae-%s.log" % (config.iface.name)
        security_config_base = '''
/* this is a comment */
authsae:
{
 sae:
  {
    debug = 480;
    password = \\"thisisreallysecret\\";
    group = [19, 26, 21, 25, 20];
    blacklist = 5;
    thresh = 5;
    lifetime = 3600;
  };
 meshd:
  {
    meshid = \\"%s\\";
    interface = \\"%s\\";
    band = \\"11g\\";
    channel = %s;
    htmode = \\"none\\";
    mcast-rate = 12;
  };
};

''' % ( str(config.ssid), str(config.iface.name), str(config.channel))
        self._cmd_or_die("echo -e \"" + security_config_base + "\"> %s" % (confpath), verbosity=0);
        self._cmd_or_die("meshd-nl80211 -c %s %s &" % (confpath, logpath))

    def mesh_join(self, config):
        cmd = "iw %s mesh join %s" % (config.iface.name, config.ssid)
        if config.mcast_rate:
            cmd +=  " mcast-rate %s" % (config.mcast_rate)
        if config.mesh_params:
            cmd += " " + config.mesh_params
        self._cmd_or_die(cmd)

# restart mesh with supplied new mesh conf with matching iface
    def reconf(self, nconf):
        # LinuxNode.shutdown()????
        self.shutdown()
        i = 0
        self.configs = [conf if conf.iface.name != nconf.iface.name else nconf for conf in self.configs]
        self.init()
        self.start()

# empty owner means just configure own owner reservation, else install
# specified interference reservation.
    def set_mcca_res(self, owner=None):
        if not self.mccapipe:
            raise node.InsufficientConfigurationError()

        if owner != None:
            self._cmd_or_die("echo i %d %d %d > %s" % (owner.res.offset,
                                                       owner.res.duration,
                                                       owner.res.period,
                                                       self.mccapipe))
        else:
            self._cmd_or_die("echo a %d %d > %s" % (self.res.duration,
                                                    self.res.period,
                                                    self.mccapipe))

    def mccatool_start(self, config=None):
        if not config:
            config = self.configs[0]
        if not self.mccapipe:
            import tempfile
            self.mccapipe = tempfile.mktemp()
            self._cmd_or_die("mkfifo %s" % self.mccapipe)
# keep the pipe open :|
            self._cmd_or_die("nohup sleep 10000 > %s &" % self.mccapipe)

        self._cmd_or_die("nohup mccatool %s > /tmp/mccatool.out 2> /dev/null < %s &" % (config.iface.name, self.mccapipe))

    def mccatool_stop(self, config=None):
        if not config:
            config = self.configs[0]
        if self.mccapipe:
            self.comm.send_cmd("killall mccatool")
            self.comm.send_cmd("rm %s" % self.mccapipe)
            self.mccapipe = None
