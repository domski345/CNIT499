import requests,pynetbox
from flask import Flask, request, jsonify
app = Flask(__name__)
project_id = "3bcd7eca-5c2e-4199-8c7d-690874e6ab72"


@app.post("/device")
def device():
    print("Yo Dawg, I heard you like routers?") # Sarcastic remark

    #Error checking
    # if request.is_json:
    #     return {"error": "Request must be JSON"}, 415

    # Get initial call from netbox webhook when device is created
    device = request.get_json()

    # Set variables accordingly
    id = device['id']
    template_id = device['device_type.slug']
    name = device['name']

    # Make API call to GNS3 to create the VM
    api_url = f"http://gns3.brownout.tech:3080/v2/projects/{project_id}/templates/{template_id}"
    data = {"x": 40, "y": 40, "name": f"{name}", "compute_id": "local"}
    response = requests.post(api_url, json=data)

    # Extract GNS3 assigned data
    node_id = response.json()["node_id"]

    # Update netbox to reflect node_id change and status
    nb = netbox
    update = {'id': f"{id}", 'serial': f"{template_id}"}
    nb.dcim.device.update(update)

    # Happy return code back to netbox
    return "Saul Goodman :)", 201

