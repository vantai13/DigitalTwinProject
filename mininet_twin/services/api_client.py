import requests
from utils.logger import setup_logger

logger = setup_logger()

class TopologyApiClient:
    """
    HTTP
    """
    def __init__(self, base_url):
        self.base_url = base_url

    def push_topology(self, net):
        """
        Gửi cấu trúc mạng (Hosts, Switches, Links) lên Backend.
        """
        logger.info(" Đang gửi topology lên Backend...")
        
        topology_data = { "hosts": [], "switches": [], "links": [] }
        
        # Hosts
        for h in net.hosts:
            topology_data["hosts"].append({
                "name": h.name,
                "ip": h.IP(),
                "mac": h.MAC()
            })
        
        # Switches
        for s in net.switches:
            topology_data["switches"].append({
                "name": s.name,
                "dpid": s.dpid
            })
        
        #  Links
        processed = set() # Set để tránh gửi trùng lặp 2 chiều của 1 dây
        for link in net.links:
            n1, n2 = link.intf1.node.name, link.intf2.node.name
            
            # Tạo ID duy nhất
            lid = "-".join(sorted([n1, n2]))
            
            if lid not in processed:
                processed.add(lid)
                bw_capacity = 100
                if n1.startswith('s') and n2.startswith('s'):
                    bw_capacity = 1000
                topology_data["links"].append({
                    "node1": n1,
                    "node2": n2,
                    "bandwidth": bw_capacity 
                })

        # Gửi request
        try:
            response = requests.post(
                f"{self.base_url}/init/topology",
                json=topology_data,
                timeout=5
            )
            response.raise_for_status()
            logger.info(f" Gửi Topology thành công: {len(net.hosts)} hosts, {len(net.switches)} switches")
            return True
        except Exception as e:
            logger.error(f" Lỗi gửi Topology: {e}")
            return False