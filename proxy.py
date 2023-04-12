import requests,pynetbox
from flask import Flask, request, jsonify
app = Flask(__name__)
project_id = "3bcd7eca-5c2e-4199-8c7d-690874e6ab72"


@app.post("/device")
def device():
    print("Yo Dawg, I heard you like routers?") # Sarcastic remark

    #Error checking
    if not request.is_json:
        return {"error": "Request must be JSON"}, 415

    # Get initial call from netbox webhook when device is created
    device = request.get_json()

    # Set variables accordingly
    id = device['id']
    template_id = device['device_type']['slug']
    name = device['name']

    # Make API call to GNS3 to create the VM
    api_url = f"http://gns3.brownout.tech:3080/v2/projects/{project_id}/templates/{template_id}"
    data = {"x": 40, "y": 40, "name": f"{name}", "compute_id": "local"}
    response = requests.post(api_url, json=data)

    # Extract GNS3 assigned data
    node_id = response.json()["node_id"]

    # Make API call to update the VM's name in GNS3
    api_url = f"http://gns3.brownout.tech:3080/v2/projects/{project_id}/nodes/{node_id}"
    data = {"name": name}
    response = requests.put(api_url, json=data)

    # Update netbox to reflect node_id change and status
    nb = pynetbox.api('http://netbox.brownout.tech:8000/', token='0123456789abcdef0123456789abcdef01234567')
    nb.dcim.devices.update([{'id': id, 'serial': node_id}])

    # Happy return code back to netbox
    return "Saul Goodman :)", 201

@app.delete("/device")
def device_delete():
    if not request.is_json:
        return {"error": "Request must be JSON"}, 415
    device = request.get_json()
    node_id = device['serial']
    api_url = f"http://gns3.brownout.tech:3080/v2/projects/{project_id}/nodes/{node_id}"
    response = requests.delete(api_url)
    return "response", 201
