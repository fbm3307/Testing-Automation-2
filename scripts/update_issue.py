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
    #GITHUB_BASE_URL = "https://api.github.com"
    headers.update({"Authorization": f'Bearer {os.environ["GITHUB_TOKEN"]}',
                    "Accept": "application/vnd.github.v3+json"})    
    if(method == "post"):
        req_method = requests.post
    elif(method == "put"):
        req_method = requests.put
    print("URL in make_github_request : ",url)
    response = req_method(url, params=params, headers=headers, json=body)
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
        output = [SUCCESS, resp_json]
    return output

def getB64(content=""):
    content = content.encode("ascii")
    content = base64.b64encode(content)
    content = content.decode('utf-8')
    return content

def getSha(filename):
    #filename = str(str(filename).split("?")[0]) # This is because github computes the SHA of latest commit, not from the current branch
    res = requests.get(filename).json()
    if("sha" in res):
        sha = res["sha"]
    else:
        sha = ""
    return sha

def update_file(filename="", content="", message="appending issue ids [skip actions]"):
    global ERROR
    global SUCCESS
    try:
        sha = getSha(filename)
        content = getB64(content)
        branch = str(filename.split("ref=")[1])
        method = "put"
        body = {"message": message,
                "content": content,
                "sha":sha,
                "branch":branch
                }
        print("Filename in target : ", filename)
        print("Sha Generated  : ", sha)
        print("Target Branch  : ", branch)
        github_output = _make_gihub_request(method=method, url=filename, body=body, verbose=False)
        status, message = github_output[0], github_output[1]
        if(status == ERROR):
            return False
        elif(status == SUCCESS):
            print("Issues appended successfully")
            return True
        # Should handle else?
    except Exception as e:
        print("Error while creating the issue " + str(e))
        return False

def add_comment_to_issue(issue_url="", comment=""):
    global ERROR
    global SUCCESS
    try:
        method = "post"
        body = {
            "body":comment
                }
        github_output = _make_gihub_request(method=method, url=issue_url, body=body, verbose=False)
        status, message = github_output[0], github_output[1]
        if(status == ERROR):
            print("Could not add the comment")
            return False
        elif(status == SUCCESS):
            print("Comment added successfully.")
            return True
        # Should handle else?
    except Exception as e:
        print("Error while adding the comment : " + str(e))
        return False
    pass
