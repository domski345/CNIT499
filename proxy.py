import requests

def main():
    print("Yo Dawg, I heard you like routers?")
    project_id = "3bcd7eca-5c2e-4199-8c7d-690874e6ab72"
    template_id = "a8bddb17-e915-4378-9870-c0fc7b413999"
    name = "api-test"
    api_url = f"http://gns3.brownout.tech:3080/v2/projects/{project_id}/templates/{template_id}"
    data = {"x": 40, "y": 40, "name": "{name}", "compute_id": "local"}
    response = requests.post(api_url, json=data)
    print(f"Return JSON:{response.json()}")
    print(f"Return JSON:{response.status_code}")

"""Do not change anything below this line."""
if __name__ == "__main__":
    main()
