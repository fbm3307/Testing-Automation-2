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
    elif(method == "patch"):
        req_method = requests.patch
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

def addComment(issue_url="", comment=""):
    issue_url = str(issue_url).strip()
    comment = str(comment).strip()
    if(issue_url == ""):
        print("[-] Found empty issue_url.")
        return False
    if(comment == ""):
        print("[-] Found empty comment.")
        return False
    body = {
        "body":comment
    }
    [status, resp] = _make_gihub_request(method="post", url=issue_url, body=body)
    if(status == SUCCESS):
        if("id" not in resp):
            #print("[-] Could not add comment to issue : " + str(issue_url))
            return False
        else:
            #print("[+] Comment added successfully to issue : " + str(issue_url))
            return True
    elif(status == ERROR):
        print("[-] Error while adding comment to the issue.")
        print("[-] Error:")
        print(json.dumps(resp, indent=4))
        return False
    else:
        return False

def closeIssue(issue_url=""):
    issue_url = str(issue_url).strip()
    if(issue_url == ""):
        print("[-] Found empty issue_url.")
        return False
    else:
        body = {
            "state":"closed"
        }
        [status, resp] = _make_gihub_request(method="patch", url=issue_url, body=body)
        if(status == SUCCESS):
            if("id" not in resp):
                #print("[-] Could not close the issue : " + str(issue_url))
                return False
            else:
                #print("[+] Issue closed successfully : " + str(issue_url))
                return True
        elif(status == ERROR):
            print("[-] Error while closing the issue.")
            print("[-] Error:")
            print(json.dumps(resp, indent=4))
            return False
        else:
            return False

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
        #print("Filename in target : ", filename)
        #print("Sha Generated  : ", sha)
        #print("Target Branch  : ", branch)
        github_output = _make_gihub_request(method=method, url=filename, body=body, verbose=False)
        status, message = github_output[0], github_output[1]
        if(status == ERROR):
            return False
        elif(status == SUCCESS):
            return True
        # Should handle else?
    except Exception as e:
        print("Error while updating file : " + str(filename))
        print("Error : " + str(e))
        return False

def create_file(filename="", content="", message="creating msg_id yml file [skip actions]"):
    global ERROR
    global SUCCESS
    try:
        content = getB64(content)
        branch = str(filename.split("ref=")[1])
        method = "put"
        body = {"message": message,
                "content": content,
                "branch":branch
                }
        #print("Filename in target : ", filename)
        #print("Sha Generated  : ", sha)
        #print("Target Branch  : ", branch)
        github_output = _make_gihub_request(method=method, url=filename, body=body, verbose=False)
        status, message = github_output[0], github_output[1]
        if(status == ERROR):
            return False
        elif(status == SUCCESS):
            return True
        # Should handle else?
    except Exception as e:
        print("Error while creating the file : " + str(filename))
        print("Error : " + str(e))
        return False

def merge_pull_request(pr_url="", commit_title="", commit_message=""):
    pr_url += "/merge"
    body = {
        "commit_title":commit_title,
        "commit_message":commit_message
    }
    method = "put"
    [isSuccess, response] = _make_gihub_request(method=method, url=pr_url, body=body)
    if(isSuccess):
        success = response["merged"]
        if(success):
            return success
        else:
            return False
    return isSuccess