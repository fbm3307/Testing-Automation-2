from os import access
import requests
import json
import os
import base64

ERROR = "error"
SUCCESS = "success"

def _make_gihub_request(method="post", url="", body=None, params={}, headers={}, verbose=False):
    output = [] # Format: ["status", "string message"]
    global ERROR
    global SUCCESS
    GITHUB_BASE_URL = "https://api.github.com"
    headers.update({"Authorization": f'Bearer {os.environ["GITHUB_TOKEN"]}',
                    "Accept": "application/vnd.github.v3+json"})    
    request_method = requests.put
    response = request_method(url, params=params, headers=headers, json=body)
    try:
        response.raise_for_status()
    except Exception as e:
        print("Exception : ", e)
    try:
        resp_json = response.json()
    except Exception:
        resp_json = None
    if resp_json and verbose:
        print(json.dumps(resp_json, indent=4, sort_keys=True))
    if("error" in resp_json):
        # Error logic
        error = resp_json["error"]
        output = [ERROR, error]
        pass
    else:
        print("Response from update_issue.py : ", resp_json)
        output = resp_json
    return output

def getB64(content=""):
    content = content.encode("ascii")
    content = base64.b64encode(content)
    content = content.decode('utf-8')
    return content

def update_file(filename="", content="", message="appending issue ids"):
    global ERROR
    global SUCCESS
    try:
        content = getB64(content)
        method = "put"
        body = {"message": message,
                "content": content
                }
        github_output = _make_gihub_request(method=method, url=filename, body=body, verbose=False)
        status, message = github_output[0], github_output[1]
        if(status == ERROR):
            return False
        elif(status == SUCCESS):
            print("Issues appended successfully")
        # Should handle else?
    except Exception as e:
        print("Error while creating the issue " + str(e))
        return False


