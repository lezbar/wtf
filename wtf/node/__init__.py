# Copyright cozybit, Inc 2010-2011
# All rights reserved

from wtf.util import *

class UninitializedError(Exception):
    """
    Exception raised when routines are called prior to initialization.
    """
    pass

class InsufficientConfigurationError(Exception):
    """
    Exception raised when sufficient configuration information is not available.
    """
    pass

class UnsupportedConfigurationError(Exception):
    """
    Exception raised when an unsupported configuration has been attempted.
    """
    pass

class ActionFailureError(Exception):
    """
    Exception raised when an action on a node fails.
    """
    pass

class UnimplementedError(Exception):
    """
    A method should have been implemented by a subclass but is not.
    """
    pass

class NodeBase():
    """
    A network node that will participate in tests

    A network node could be an AP, a mesh node, a client STA, or some new thing
    that you are inventing.  Minimally, it can be initialized and shutdown
    repeatedly.  So init and shutdown are really not the same thing as __init__
    and __del__.  Once a node has been successfully initialized, it can be
    started and stopped, repeatedly.
    """

    def __init__(self, comm):
        self.initialized = False
        self.comm = comm

    def init(self):
        """
        initialize the node

        override this method to customize how your node is initialized.  For
        some nodes, perhaps nothing is needed.  Others may have to be powered
        on and configured.
        """
        self.initialized = True

    def shutdown(self):
        """
        shutdown the node

        override this method to customize how your node shuts down.
        """
        self.initialized = False

    def start(self):
        """
        start the node in its default configuration

        raises an UninitializedError if init was not called.

        raises an InsufficientConfigurationError exception if sufficient
        default values are not available.
        """
        if self.initialized != True:
            raise UninitializedError()
        raise InsufficientConfigurationError()

    def stop(self):
        """
        stop the node
        """
        pass

    def set_ip(self, iface, ipaddr):
        """
        set the ip address of a node
        """
        raise UnimplementedError("set_ip is not implemented for this node")

    def ping(self, host, timeout=2, count=1):
        """
        ping a remote host from this node

        timeout: seconds to wait before quitting

        count: number of ping requests to send

        return 0 on success, anything else on failure
        """
        raise UnimplementedError("ping is not implemented for this node")

    def _cmd_or_die(self, cmd, verbosity=None):
        (r, o) = self.comm.send_cmd(cmd, verbosity)
        if r != 0:
            raise ActionFailureError("Failed to \"" + cmd + "\"")
        return o

# wifi interface with associated driver and ip and maybe a monitor interface
class Iface():
    def __init__(self, name=None, driver=None, ip=None, conf=None):
        if not name:
            raise InsufficientConfigurationError("need iface name")
        if not driver:
            raise InsufficientConfigurationError("need iface driver")
        self.ip = ip
        self.name = name
        self.driver = driver
        self.conf = conf
        self.enable = True
        self.perf = None
        self.node = None
        self.phy = None
        self.mac = None
        self.monif = None
        self.local_cap = None

    def start_perf(self, conf):
        if conf.dst_ip == None:
            conf.dst_ip = self.ip
        self.perf = conf
        self.perf.log = "/tmp/iperf_" + self.name + ".log"
        if conf.server == True:
            cmd = "iperf -s -p" + str(conf.listen_port)
            if conf.tcp != True:
                cmd += " -u"
            if conf.dst_ip:
                cmd += " -B" + conf.dst_ip
# -x  [CDMSV]   exclude C(connection) D(data) M(multicast) S(settings) V(server) reports
            cmd += " -y c -x CS > " + self.perf.log
            cmd += " &"
        else:
# in o11s the mpath expiration is pretty aggressive (or it hasn't been set up
# yet), so prime it with a ping first. Takes care of initial "losses" as the
# path is refreshed.
            self.node.ping(conf.dst_ip, verbosity=3, timeout=10, count=10)
            self.dump_mpaths()
            cmd = "iperf -c " + conf.dst_ip + \
                  " -i1 -t" + str(conf.timeout) + \
                  " -p" + str(conf.listen_port)
            if conf.tcp != True:
                cmd += " -u -b" + str(conf.bw) + "M"
            if conf.dual:
                cmd += " -d -L" + str(conf.dual_port)
            if conf.fork:
                cmd += " &"

        r, o = self.node.comm.send_cmd(cmd)
        if conf.server != True and conf.fork != True:
# we blocked on completion and report is ready now
            self.perf.report = o[1]
        else:
            r, o = self.node.comm.send_cmd("echo $!")
            self.perf.pid =  int(o[0])

    def perf_serve(self, dst_ip=None, p=7777, tcp=False):
        self.start_perf(PerfConf(server=True, dst_ip=dst_ip, p=p, tcp=tcp))

    def perf_client(self, dst_ip=None, timeout=5, dual=False, b=10, p=7777, L=6666, fork=False,
                    tcp=False):
        if dst_ip == None:
            raise InsufficientConfigurationError("need dst_ip for perf")
        self.start_perf(PerfConf(dst_ip=dst_ip, timeout=timeout,
                                 dual=dual, b=b, p=p, L=L, fork=fork,
                                 tcp=tcp))

    def killperf(self):
        if self.perf.pid == None:
            return
        self.node.comm.send_cmd("while kill %d 2>/dev/null; do sleep 1; done" % (self.perf.pid,))
        self.perf.pid = None

    def get_perf_report(self):
        self.killperf()
        r, o = self.node.comm.send_cmd("cat " + self.perf.log)
        print "parsing perf report"
        return parse_perf_report(self.perf, o)

# server @video to @dst_ip using VLC. Blocks until stream completion
    def video_serve(self, video=None, ip=None, port=5004):
        if ip == None or video == None:
            raise InsufficientConfigurationError("need a reference clip and destination ip!")
        print "%s: starting video server" % (self.ip,)
        import os
        self.ref_clip = "/tmp/" + os.path.basename(video)
        self.comm.put_file(video, self.ref_clip)
# prime mpath so we don't lose inital frames in unicast!
        self.node.ping(ip, verbosity=0)
        self.node.comm.send_cmd("su nobody -c 'vlc -I dummy %s :sout=\"#rtp{dst=%s,port=%d,mux=ts,ttl=1}\" :sout-all :sout-keep vlc://quit' &> /tmp/video.log" % (self.ref_clip, ip, port))

    def video_client(self, out_file=None, ip=None, port=5004):
        print "%s: starting video client" % (self.ip,)
        if ip == None:
            raise InsufficientConfigurationError("need a reference clip and destination ip!")
        if out_file == None:
            out_file = "/tmp/" + self.name + "_video.ts"
        self.video_file = out_file
        self.node.comm.send_cmd("su nobody -c 'vlc -I dummy rtp://%s:%d --sout file/ts:%s' &> /tmp/video.log &" % (ip, port, self.video_file))

    def killvideo(self):
        self.node.comm.send_cmd("killall -w vlc")
        self.node.comm.send_cmd("cat /tmp/video.log")

    def get_video(self, path="/tmp/out.ts"):
        if self.video_file == None:
            pass
        self.killvideo()
        self.node.comm.get_file(self.video_file, path)

    def start_capture(self, cap_file=None):
        if cap_file == None:
            cap_file = "/tmp/" + self.name + "_out.cap"
        self.cap_file = cap_file
        if not self.monif:
            self.monif = self.name + ".mon"
            self.node._cmd_or_die("iw " + self.name + " interface add " + self.monif + " type monitor")
            self.node._cmd_or_die("ip link set " + self.monif + " up")

        self.node._cmd_or_die("tcpdump -i " + self.monif + " -ll -xx -p -U -w " + self.cap_file + " &")

# return path to capture file now available on local system
    def get_capture(self, path=None):
        if not path:
            import tempfile
            path = tempfile.mktemp()
        self.node.comm.get_file(self.cap_file, path)
# save a pointer
        self.local_cap = path
        return path

# stop capture and get a copy for analysis
    def stop_capture(self, path=None):
        if not self.monif:
            return
        self.node.comm.send_cmd("killall -9 tcpdump")
        return self.get_capture(path)

    # XXX: ahem, mesh-specific goes in MeshIface?
    def add_mesh_peer(self, peer):
        self.node.comm.send_cmd("iw %s station set %s plink_action open" %
                                (self.name, peer.mac))


class LinuxNode(NodeBase):
    """
    A linux network node

    Expects: iw, mac80211 debugfs
    """
    def __init__(self, comm, ifaces=[], path=None):
        self.iface = ifaces
        self.brif = None
        NodeBase.__init__(self, comm)
        if path != None:
            self.comm.send_cmd("export PATH=" + path + ":$PATH:", verbosity=0)

        # who knows what was running on this machine before.  Be sure to kill
        # anything that might get in our way.
        self.comm.send_cmd("killall hostapd; killall wpa_supplicant",
                           verbosity=0)

    def init(self):
        for iface in self.iface:
            if iface.enable != True:
                continue
            self._cmd_or_die("modprobe " + iface.driver)
            # give ifaces time to come up
            import time
            time.sleep(1)
            # TODO: check for error and throw something!
            r, iface.phy = self.comm.send_cmd("echo `find /sys/kernel/debug/ieee80211 -name netdev:" + iface.name + " | cut -d/ -f6`", verbosity=0)
            r, iface.mac = self.comm.send_cmd("echo `ip link show " + iface.name + " | awk '/ether/ {print $2}'`", verbosity=0)

            # XXX: Python people help!!
            iface.phy = iface.phy[0]
            iface.mac = iface.mac[0]
            iface.node = self

        self.initialized = True

    def shutdown(self):
        self.stop()
        for iface in self.iface:
            if iface.driver:
                self.comm.send_cmd("modprobe -r " + iface.driver)
        # stop meshkitd in case it's installed
        self.comm.send_cmd("/etc/init.d/meshkit stop")
        self.initialized = False

    def start(self):
        if self.initialized != True:
            raise UninitializedError()
        for iface in self.iface:
            if iface.enable != True:
                continue
            # FIXME: config.iface.set_ip()?
            self.set_ip(iface.name, iface.ip)
            if iface.conf.mcast_route:
                self.set_mcast(iface, iface.conf.mcast_route)

    def stop(self):
        for iface in self.iface:
            self.comm.send_cmd("ifconfig " + iface.name + " down")
        self.del_brif()

    def set_ip(self, name, ipaddr):
        self.comm.send_cmd("ifconfig " + name + " " + ipaddr + " up")

    def set_mcast(self, iface, mcast_route):
        self.comm.send_cmd("route add -net %s netmask 255.255.255.255 %s" % (mcast_route, iface.name))

    def ping(self, host, timeout=2, count=1, verbosity=2):
        return self.comm.send_cmd("ping -c " + str(count) + " -w " +
                                  str(timeout) + " " + host, verbosity=verbosity)[0]

    def if_down(self, iface):
        self.comm.send_cmd("ifconfig " + iface + " down")

    def del_brif(self):
        if not self.brif:
            return
        self.if_down(self.brif)
        self.comm.send_cmd("brctl delbr " + self.brif)

# bridge interfaces in ifaces[] and assign ip
    def bridge(self, ifaces, ip):
        bridge="br0"
        self.del_brif();
        self.brif = bridge
        self._cmd_or_die("brctl addbr " + bridge)
        for iface in ifaces:
            self._cmd_or_die("ip addr flush " + iface.name)
            self._cmd_or_die("brctl addif %s %s " % (bridge, iface.name))
        self.set_ip("br0", ip)

    def bond_reload(self):
        self.comm.send_cmd("modprobe -r bonding")
        self.comm.send_cmd("modprobe bonding")

# bond interfaces in ifaces[] and assign ip
    def bond(self, ifaces, ip):
        self.bond_reload()
        self.set_ip("bond0", ip)
        for iface in ifaces:
            self._cmd_or_die("ip addr flush " + iface.name)
            self._cmd_or_die("ifenslave bond0 " + iface.name)
