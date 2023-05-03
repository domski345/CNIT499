import requests,pynetbox,random, json, threading, ipaddress
from flask import Flask, request, jsonify
from telnetlib import Telnet
from napalm import get_network_driver
from jinja2 import Template
application = Flask(__name__)
project_id = "3bcd7eca-5c2e-4199-8c7d-690874e6ab72"
nb = pynetbox.api('http://netbox.brownout.tech:8000/', token='0123456789abcdef0123456789abcdef01234567')


@application.post("/device")
def device():
    print("Yo Dawg, I heard you like routers?") # Sarcastic remark

    #Error checking
    if not request.is_json:
        return {"error": "Request must be JSON"}, 415

    # Get initial call from netbox webhook when device is created
    device = request.get_json()

    # Set variables accordingly
    id = device['data']['id']
    template_id = device['data']['device_type']['slug']
    name = device['data']['name']

    # Make API call to GNS3 to create the VM
    api_url = f"http://gns3.brownout.tech:3080/v2/projects/{project_id}/templates/{template_id}"
    data = {"x": random.randrange(-800,800), "y": random.randrange(-500,500), "name": f"{name}", "compute_id": "local"}
    response = requests.post(api_url, json=data)

    # Extract GNS3 assigned data
    node_id = response.json()["node_id"]
    console = response.json()["console"]

    # Generate mac address for mgmt nic
    mac_address = "00:20:91:%02x:%02x:%02x" % (random.randint(0, 255),random.randint(0, 255),random.randint(0, 255))
    options = f"-nic bridge,br=br0,model=e1000,mac={mac_address}"

    # Make API call to update the VM's name in GNS3
    api_url = f"http://gns3.brownout.tech:3080/v2/projects/{project_id}/nodes/{node_id}"
    data = {"name": name, "properties": { "options": options } }
    response = requests.put(api_url, json=data)

    # Update netbox to reflect node_id change and status
    nb.dcim.devices.update([{'id': id, 'serial': node_id, 'asset_tag': console}])

    # Begin ZTP
    api_url = f"http://gns3.brownout.tech:3080/v2/projects/{project_id}/nodes/{node_id}/start"
    requests.post(api_url)

    primary_ip6 = nb.ipam.prefixes.get(2).available_ips.create()
    int_id = nb.dcim.interfaces.get(device_id=id,name="MgmtEth0/0/CPU0/0")['id']
    nb.ipam.ip-addresses.update([{'address': primary_ip6, 'vrf': 1, 'assigned_object_type': 'dcim.interface', 'assigned_object_id': int_id}])
    device_args=[console,name,primary_ip6,id]
    configure_thread = threading.Thread(target=configure, name="configure_device", args=device_args)
    configure_thread.start()

    # Happy return code back to netbox
    return f"Node {node_id} was created", 201

@application.delete("/device")
def device_delete():
    if not request.is_json:
        return {"error": "Request must be JSON"}, 415
    device = request.get_json()
    node_id = device['data']['serial']
    requests.post(f"http://gns3.brownout.tech:3080/v2/projects/{project_id}/nodes/{device['data']['serial']}/stop")
    name = device['data']['name']
    api_url = f"http://gns3.brownout.tech:3080/v2/projects/{project_id}/nodes/{node_id}"
    requests.delete(api_url)
    return f"{name} was deleted", 201

@application.post("/cable")
def cable():
    print("Yo Dawg, I heard you like cables?") # Sarcastic remark

    #Error checking
    if not request.is_json:
        return {"error": "Request must be JSON"}, 415
    
    cable = request.get_json()

    id = cable['data']['id']
    a_node_id = cable['data']['a_terminations'][0]['object']['device']['id']
    b_node_id = cable['data']['b_terminations'][0]['object']['device']['id']
    a_interface_id = cable['data']['a_terminations'][0]['object_id']
    b_interface_id = cable['data']['a_terminations'][0]['object_id']

    # Get necessary data from netbox
    a_id = nb.dcim.devices.get(id=a_node_id)['serial']
    b_id = nb.dcim.devices.get(id=b_node_id)['serial']
    a_label = nb.dcim.interfaces.get(id=a_interface_id)['label']
    b_label = nb.dcim.interfaces.get(id=b_interface_id)['label']

    # Make API call to update the VM's name in GNS3
    api_url = f"http://gns3.brownout.tech:3080/v2/projects/{project_id}/links"
    data = {"nodes": [{ "node_id": a_id, "adapter_number": int(a_label), "port_number": 0 }, { "node_id": b_id, "adapter_number": int(b_label), "port_number": 0 }]}
    response = requests.post(api_url, json=data)

    # Extract GNS3 assigned data
    link_id = response.json()["link_id"]

    # pull management ip address from devices on cable
    mgmt_ip_a = ipaddress.IPv6Interface(nb.dcim.devices.get(id=a_node_id)['primary_ip6']['address']).ip
    mgmt_ip_b = ipaddress.IPv6Interface(nb.dcim.devices.get(id=b_node_id)['primary_ip6']['address']).ip 
    # driver = nb.dcim.devices.get(id=device_id)['platform']['slug'] # Assume single vendor environment
    driver = "iosxr"

    # generate v6 prefix for link
    prefix = nb.ipam.prefixes.get(6).available_prefixes.create({"prefix_length": 127})
    # generate ip addresses from prefix
    ip_a_side = prefix.available_ips.create()
    ip_b_side = prefix.available_ips.create()

    # push ip address changes to Netbox
    nb.ipam.ipaddresses.update([{'address': ip_a_side, 'vrf': 1, 'assigned_object_type': 'dcim.interface', 'assigned_object_id': a_interface_id}])
    nb.ipam.ipaddresses.update([{'address': ip_b_side, 'vrf': 1, 'assigned_object_type': 'dcim.interface', 'assigned_object_id': b_interface_id}])

    # configuration data for "a" side device
    data_a = {
        "ip": ip_a_side,
        "vrf": "mgmt",
        "iface": cable['data']['a_terminations'][0]['object']['name']
    } 

    # configuration data for "b" side device
    data_b = {
        "ip": ip_b_side,
        "vrf": "mgmt",
        "iface": cable['data']['b_terminations'][0]['object']['name']
    }

    # configuration template
    template = """
interface {{ iface }}
{% if vrf %} vrf {{ vrf }}{% endif %}
 ipv6 address {{ ip }}
 no shutdown
"""
    j2_template = Template(template)
    device_driver = get_network_driver(driver)

    # write changes to "a" side device
    device_a = device_driver(hostname=mgmt_ip_a,username='cisco',password='cisco')
    device_a.open()
    device_a.load_merge_candidate(config=j2_template.render(data_a))
    device_a.commit_config()
    device_a.close()

    # write changes to "b" side device
    device_b = device_driver(hostname=mgmt_ip_b,username='cisco',password='cisco')
    device_b.open()
    device_b.load_merge_candidate(config=j2_template.render(data_b))
    device_b.commit_config()
    device_b.close()


    # Update netbox with the cable ID
    nb.dcim.cables.update([{'id': id, 'label': link_id}])
    return f"Cable: {link_id} was created", 201


@application.delete("/cable")
def cable_delete():
    if not request.is_json:
        return {"error": "Request must be JSON"}, 415
    device = request.get_json()
    link_id = device['data']['label']
    api_url = f"http://gns3.brownout.tech:3080/v2/projects/{project_id}/links/{link_id}"
    requests.delete(api_url)
    return f"{link_id} was deleted", 201

# IP address config
@application.post("/ip")
def ip():
    print("Yo Dawg, I heard you like IP addresses?") # Sarcastic remark

    #Error checking
    if not request.is_json:
        return {"error": "Request must be JSON"}, 415
    
    conf = request.get_json()
    device_id = conf['data']['assigned_object']['device']['id'],
    mgmt_ip = ipaddress.IPv6Interface(nb.dcim.devices.get(id=device_id)['primary_ip6']['address']).ip
    driver = nb.dcim.devices.get(id=device_id)['platform']['slug']
    data = {
        "ip": conf['data']['address'],
        "vrf": conf['data']['vrf']['name'],
        "family": conf['data']['family']['value'],
        "iface": conf['data']['assigned_object']['name']
    } 
    template = """
interface {{ iface }}
{% if vrf %} vrf {{ vrf }}{% endif %}
 ipv{{ family }} address {{ ip }}
 no shutdown
"""
    j2_template = Template(template)
    device_driver = get_network_driver(driver)
    device = device_driver(hostname=mgmt_ip,username='cisco',password='cisco')
    device.open()
    device.load_merge_candidate(config=j2_template.render(data))
    device.commit_config()
    device.close()

    return f"{ip} is being configured", 201

@application.patch("/device")
def device_update():
    print("Oh no") # Sarcastic remark

    #Error checking
    if not request.is_json:
        return {"error": "Request must be JSON"}, 415
    
    update = request.get_json()
    if update['data']['status']['value'] == 'staged':
        print("help")
    return f"{update['data']['name']} is being configured", 201

# Debug
@application.post("/debug")
def debug():
    print("Uh Oh") # Sarcastic remark

    print(json.dumps(request.get_json(),indent=4))
    return "debug'd!", 201

def configure(port,hostname,ip6,id):
        tn = Telnet('gns3.brownout.tech', port)
        tn.read_until(b"Press RETURN to get started")
        tn.write(b"\r")
        tn.read_until(b"Enter root-system username:")
        tn.write(b"drusso\r")
        tn.read_until(b":")
        tn.write(b"cisco!123\r")
        tn.read_until(b":")
        tn.write(b"cisco!123\r")
        tn.read_until(b"SYSTEM CONFIGURATION COMPLETED", timeout=120)
        tn.write(b"\r")
        tn.read_until(b"Username:")
        tn.write(b"cisco\r")
        tn.read_until(b"Password:")
        tn.write(b"cisco\r")
        tn.read_until(b"#")
        tn.write(b"config\r")
        tn.read_until(b"#")
        tn.write(f"hostname {hostname}\n".encode('utf8'))
        tn.read_until(b"#")
        tn.write(b"vrf Mgmt address-family ipv6 unicast\r")
        tn.read_until(b"#")
        tn.write(b"exit\r")
        tn.read_until(b"#")
        tn.write(b"address-family ipv4 unicast\r")
        tn.read_until(b"#")
        tn.write(b"exit\r")
        tn.read_until(b"#")
        tn.write(b"exit\r")
        tn.read_until(b"#")
        tn.write(b"router static vrf Mgmt address-family ipv6 unicast ::/0 2602:fe6a:301:1::1\r")
        tn.read_until(b"#")
        tn.write(b"interface MgmtEth0/0/CPU0/0\r")
        tn.read_until(b"#")
        tn.write(b"vrf Mgmt\r")
        tn.read_until(b"#")
        tn.write(f"ipv6 address {ip6}\n".encode('utf8'))
        tn.read_until(b"#")
        tn.write(b"no shut\n")
        tn.read_until(b"#")
        tn.write(b"exit\n")
        tn.read_until(b"#")
        tn.write(b"ssh server v2\n")
        tn.read_until(b"#")
        tn.write(b"ssh server vrf Mgmt\n")
        tn.read_until(b"#")
        tn.write(b"lldp\n")
        tn.read_until(b"#")
        tn.write(b"exit\n")
        tn.read_until(b"#")
        tn.write(b"xml agent tty iteration off\n")
        tn.read_until(b"#")
        tn.write(b"xml agent vrf Mgmt\n")
        tn.read_until(b"#")
        tn.write(b"end\n")
        tn.read_until(b":")
        tn.write(b"yes\n")
        tn.read_until(b"#")
        tn.write(b"crypto key generate rsa\n")
        tn.read_until(b":")
        tn.write(b"\n")
        tn.read_until(b"#")
        tn.write(b"exit\n")
        tn.close()

        nb.dcim.devices.update([{'id': id, 'status': "planned", 'primary_ip6': ip6}])



#def configurejunos():