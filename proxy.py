import requests,pynetbox,random
from flask import Flask, request, jsonify
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

    # Make API call to update the VM's name in GNS3
    api_url = f"http://gns3.brownout.tech:3080/v2/projects/{project_id}/nodes/{node_id}"
    data = {"name": name}
    response = requests.put(api_url, json=data)

    # Update netbox to reflect node_id change and status
    nb.dcim.devices.update([{'id': id, 'serial': node_id}])

    # Happy return code back to netbox
    return f"Node {node_id} was created", 201

@application.delete("/device")
def device_delete():
    if not request.is_json:
        return {"error": "Request must be JSON"}, 415
    device = request.get_json()
    node_id = device['data']['serial']
    name = device['data']['name']
    api_url = f"http://gns3.brownout.tech:3080/v2/projects/{project_id}/nodes/{node_id}"
    requests.delete(api_url)
    return f"{name} was deleted", 201

@application.post("/cable")
def device():
    print("Yo Dawg, I heard you like cables?") # Sarcastic remark

    #Error checking
    if not request.is_json:
        return {"error": "Request must be JSON"}, 415
    
    cable = request.get_json()

    id = cable['data']['id']
    a_node_id = cable['data']['a_terminations']['object']['device']['id']
    b_node_id = cable['data']['b_terminations']['object']['device']['id']
    a_interface_id = cable['data']['a_terminations']['object']['id']
    b_interface_id = cable['data']['a_terminations']['object']['id']
    # print(nb.dcim.devices.get(a_node_id))

    a_label = nb.dcim.interfaces.get(id=a_interface_id)['label']
    b_label = nb.dcim.interfaces.get(id=b_interface_id)['label']

    # Make API call to update the VM's name in GNS3
    api_url = f"http://gns3.brownout.tech:3080/v2/projects/{project_id}/links"
    data = {"nodes": [{ "node_id": a_node_id, "adapter_number": a_label, "port_number": 0 }, { "node_id": b_node_id, "adapter_number": b_label, "port_number": 0 }]}
    response = requests.put(api_url, json=data)

    # Extract GNS3 assigned data
    link_id = response.json()["link_id"]

    # Update netbox with the cable ID
    nb.dcim.interfaces.update([{'id': id, 'label': link_id}])
    return f"Cable: {link_id} was created", 201