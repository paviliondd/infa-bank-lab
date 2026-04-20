import yaml, os, datetime
from netmiko import ConnectHandler

def load_inventory(filepath):
    with open(filepath, 'r') as file:
        return yaml.safe_load(file)

def extract_hosts(inventory_data):
    hosts = []
    # Quét định dạng 1: Group lồng trong children
    children = inventory_data.get('all', {}).get('children', {})
    for group, group_info in children.items():
        if not isinstance(group_info, dict): continue
        for hostname, host_info in group_info.get('hosts', {}).items():
            if not isinstance(host_info, dict): continue
            hosts.append({
                'hostname': hostname,
                'ip': host_info.get('ansible_host'),
                'type': 'firewall' if 'fw' in hostname.lower() else 'router_switch'
            })
            
    # Quét định dạng 2: host trực tiếp dưới all
    all_hosts = inventory_data.get('all', {}).get('hosts', {})
    for hostname, host_info in all_hosts.items():
        if not isinstance(host_info, dict): continue
        if not any(h['hostname'] == hostname for h in hosts):
            hosts.append({
                'hostname': hostname,
                'ip': host_info.get('ansible_host'),
                'type': 'firewall' if 'fw' in hostname.lower() else 'router_switch'
            })
    return hosts

def backup_device(device_info, base_path):
    print(f"\n[*] Đang thực hiện backup cho thiết bị: {device_info['hostname']} ({device_info['ip']})")
    node = {
        'device_type': 'linux', 'host': device_info['ip'],
        'username': 'root', 'password': 'root', # Sửa pass/user ở đây nếu có
        'global_delay_factor': 2,
    }
    
    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_dir = os.path.join(base_path, device_info['hostname'])
    if not os.path.exists(backup_dir): os.makedirs(backup_dir)
        
    try:
        print("  -> Bắt đầu kết nối Netmiko (SSH)...")
        net_connect = ConnectHandler(**node)
        
        print("  -> Kéo file định tuyến frr.conf...")
        frr_config = net_connect.send_command("vtysh -c 'show running-config'")
        with open(os.path.join(backup_dir, f"frr_latest.conf"), 'w') as f: f.write(frr_config)
        
        if device_info['type'] == 'firewall':
            print("  -> Kéo cấu hình IPTABLES...")
            iptables_rules = net_connect.send_command("iptables-save")
            with open(os.path.join(backup_dir, f"iptables_latest.rules"), 'w') as f: f.write(iptables_rules)
            
        net_connect.disconnect()
        print(f"  [+] Đã lưu cấu hình tại: {backup_dir}")
    except Exception as e:
        print(f"  [-] Lỗi kết nối tới {device_info['hostname']}: {str(e)}")

script_dir = os.path.dirname(os.path.realpath(__file__))
inv_file = os.path.join(script_dir, 'inventory.yml')

try:
    inventory_data = load_inventory(inv_file)
    hosts = extract_hosts(inventory_data)
    
    print(f"[DEBUG] Đã scan thấy {len(hosts)} Node mạng trong cấu hình inventory.yml")
    if len(hosts) == 0:
         print(f"[ERROR] Dữ liệu trong JSON đọc được: {inventory_data}")
         print("[ERROR] Script không lấy được thiết bị nào! Vui lòng kiểm tra lại cấu trúc file inventory.yml")
         exit(1)
         
    backup_base_dir = os.path.join(script_dir, 'backups')
    for host in hosts:
        backup_device(host, backup_base_dir)
    print("\n[✓] QUÁ TRÌNH BACKUP HOÀN TẤT.")
except Exception as e:
    print(f"\n[!] LỖI HỆ THỐNG CRITICAL: {e}")
