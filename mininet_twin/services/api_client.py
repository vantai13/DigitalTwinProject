import requests
import config
from utils.logger import logger


def push_topology(net):
    """Gửi cấu trúc mạng lên Backend qua HTTP"""
    logger.info(" Đang gửi topology lên Backend...")
    topology_data = { "hosts": [], "switches": [], "links": [] }
    for h in net.hosts:
        topology_data["hosts"].append({
            "name": h.name,
            "ip": h.IP(),
            "mac": h.MAC()
        })
    
    for s in net.switches:
        topology_data["switches"].append({
            "name": s.name,
            "dpid": s.dpid
        })
    
    processed = set() # để tránh 2 dây trùng nhau 
    for link in net.links:
        n1, n2 = link.intf1.node.name, link.intf2.node.name
        lid = "-".join(sorted([n1, n2]))
        if lid not in processed:
            processed.add(lid)
            topology_data["links"].append({
                "node1": n1,
                "node2": n2,
                "bandwidth": 100
            })

    try:
        response = requests.post(
            f"{config.API_BASE_URL}/init/topology",
            json=topology_data,
            timeout=5
        )
        response.raise_for_status()
        logger.info(f" Gửi Topology thành công: {len(net.hosts)} hosts, {len(net.switches)} switches")
        return True
    except Exception as e:
        logger.error(f" Lỗi gửi Topology: {e}")
        return False