import wtf
import wtf.node.ap
import wtf.comm
import wtf.node.sta
from wtf.node import PlatformOps

ap_ssh = wtf.comm.SSH(ipaddr="127.0.0.1", username="vagrant", port=2203)
ap_ssh.name = "host-ap"
ap_ssh.verbosity = 2

ap_iface = []
# iface + ip
ap_iface.append(wtf.node.Iface(name="wlan0", driver="mac80211_hwsim", ip="11.11.11.11"))
ap = wtf.node.ap.Hostapd(ap_ssh, ap_iface)



sta_ssh = wtf.comm.SSH(ipaddr="127.0.0.1", username="vagrant", port=2203)
sta_ssh.name = "sta"
sta_ssh.verbosity = 2
sta_iface = []
# iface + ip
sta_iface.append(wtf.node.Iface(name="wlan1", driver="mac80211_hwsim", ip="11.11.11.13"))

sta = wtf.node.sta.LinuxSTA(sta_ssh, sta_iface)
wtf.conf = wtf.config("ap_sta", nodes=[ap, sta], name="hostapd as AP tests")
