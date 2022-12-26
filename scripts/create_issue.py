from os import access
import requests
import json
import os

ERROR = "error"
SUCCESS = "success"

def _make_gihub_request(method="post", uri="issues", body=None, params={}, headers={}, verbose=False, repo=""):
    output = [] # Format: ["status", "string message"]
    global ERROR
    global SUCCESS
    GITHUB_BASE_URL = "https://api.github.com"
    headers.update({"Authorization": f'Bearer {os.environ["GITHUB_TOKEN"]}',
                    "Accept": "application/vnd.github.v3+json"})    
    print(headers)
    url = f'{GITHUB_BASE_URL}/repos/{repo}/{uri}'
    print(f"API url: https://github.com/{repo}/{uri}")
    request_method = requests.post
    response = request_method(url, params=params, headers=headers, json=body)
    try:
        response.raise_for_status()
    except Exception as e:
        print("Exeption : ", e)
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
    elif("number" in resp_json and "url" in resp_json):
        # Get issue number
        url = resp_json["url"]
        output = [SUCCESS, url]
        pass
    # Output format
    # Error: ["error", "error message"]
    # Success: ["success", "issue_id_url"]
    return output

def create_an_issue(title, description="Description", repo=""):
    global ERROR
    global SUCCESS
    try:
        uri = "issues"
        method = "post"
        body = {"title": title,
                "body": description
                }
        github_output = _make_gihub_request(method, uri, body=body, verbose=False, repo=repo)
        status, message = github_output[0], github_output[1]
        if(status == ERROR):
            return False
        elif(status == SUCCESS):
            issueUrl = message
            issueUrl = "https://github.com/" + str(issueUrl.split("repos/")[1])
            return [True, issueUrl]
        # Should handle else?
    except Exception as e:
        print("Error while creating the issue " + str(e))
        return False
