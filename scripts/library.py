from email.mime import image
import os
from re import template
import re
import sys
from typing import final
from uuid import uuid4
from wsgiref import headers
import yaml
import requests
import argparse
from create_issue import *
from update_issue import *
import random
import time
import base64

parser = argparse.ArgumentParser()
parser.add_argument("--pr_url", help="Name of the yaml file which triggered this action")
parser.add_argument("--branch", help="Source branch from where PR is generated")
args = parser.parse_args()

pr_url = args.pr_url
source_branch = args.branch
print("Received Data: ", pr_url)
gFilename = "" # This will be used whie updating the issue.
gMessageId = "" # This variable will store the message id (either newly generated or previously generated)
MAX_RANDOM = 1000000
VALID_OPERATIONS = ["create_issues", "comment", "close_issues"]
VALID_RECEPIENT_TYPE = ["testtemplates", "testimagestreams", "testall"]
PR_MERGE_COMMIT_TITLE = "Merging through workflow [skip action]"
PR_MERGE_COMMIT_MESSAGE = "Merging through workflow [skip action]"

try:
    from yaml import CLoader as Loader, CDumper as Dumper
except ImportError:
    from yaml import Loader, Dumper

imageStreamDict = {}
templateDict = {}
combinedDict = {}
testimagestreamsDict = {"testimage":["fbm3307/test-learn"], "testimagest":["fbm3307/testimagestreams1"]}
testtemplatesDict = {"testtemplate":["fbm3307/testtemplates"]}
testallDict = {"testimage":["fbm3307/test-learn"], "testimagest":["fbm3307/testimagestreams1"], "testtemplate":["fbm3307/testtemplates"]}
allowed_inputs = ["image_stream", "templates", "all"]


def load_openshift_yaml():
    global imageStreamDict
    global templateDict
    global combinedDict

    print("Loading the repo list from official.yaml")

    LIBRARY_FILE= requests.get("https://github.com/openshift/library/blob/master/official.yaml?raw=true")
    filedata = yaml.safe_load(LIBRARY_FILE.text)
    githubcontent=filedata["data"]
    
    for reponame in githubcontent:
        imagestreamLocationSet = set() #Initialize the locationSet
        if("imagestreams" in githubcontent[reponame]):
            #code for imagestream
            for ele in githubcontent[reponame]["imagestreams"]:
                location = ele["location"]
                temp = (str(location).split("//")[1]).split("/")
                repo1,repo2 = temp[1], temp[2]
                finalUrl = f"{str(repo1)}/{str(repo2)}"
                imagestreamLocationSet.add(finalUrl)
            imageStreamDict[reponame] = list(imagestreamLocationSet)
        templateLocationSet = set() #Re-Initialize the location list
        if("templates" in githubcontent[reponame]):
            #code for templates
            for ele in githubcontent[reponame]["templates"]:
                location = ele["location"]
                temp = (str(location).split("//")[1]).split("/")
                repo1,repo2 = temp[1], temp[2]
                finalUrl = f"{str(repo1)}/{str(repo2)}"
                templateLocationSet.add(finalUrl)
            templateDict[reponame] = list(templateLocationSet)
        imagestreamLocationSet.update(templateLocationSet)
        combinedDict[reponame] = list(imagestreamLocationSet)
    print("completed the division of the  repos into imagestreams and templates")


def target_repos(user_input="", issueTitle="", issueDescription=""):
    if(user_input == ""):
        return False
    output = [] # output = {repo_url:issue_id_url}
    targetDict = {}
    if(user_input == "all"):
        targetDict = combinedDict
        print("Going to create the issue in ALL combined target repos")
    elif(user_input == "templates"):
        targetDict = templateDict
        print("Going to create the issue in Template target repos")
    elif(user_input == "imagestreams"):
        targetDict = imageStreamDict
        print("Going to create the issue in Imagestreams target repos")
    elif(user_input == "testimagestreams"):
        targetDict = testimagestreamsDict
        print("Going to create the issue in Testimagestreams target repos")
    elif(user_input == "testtemplates"):
        targetDict = testtemplatesDict
        print("Going to create the issue in TestTemplate target repos")
    elif(user_input == "testall"):
        targetDict = testallDict
        print("Going to create the issue in TestAll target repos")
    else:
        print("Invalid input")
        exit()
    return targetDict
    

def read_yml_file(file_url=""):
    sample_msg_file_content = ""
    filename = ""
    try:
        headers = {'Accept': 'application/vnd.github.v3+json'}
        response = requests.get(file_url, headers=headers)
        response = response.json()
        file_content = response["content"]
        file_content = base64.b64decode(file_content)
        return file_content
    except Exception as e:
        print("error : " + str(e))
        return ""

def get_yaml_from_pr(pr_url=""):
    sample_msg_file_content = ""
    filename = ""
    try:
        pr_file_url = pr_url + "/files"
        headers = {'Accept': 'application/vnd.github.v3+json'}
        pr_files = requests.get(pr_file_url, headers=headers)
        files = pr_files.json()
        for file in files:
            filename = file["filename"]
            validFile = filename.startswith("message/") and filename.endswith(".yml")
            if(not validFile):
                continue
            raw_url = file['raw_url']
            sample_msg_file_content = requests.get(raw_url, headers=headers).text
            #print("File Content : ", sample_msg_file_content)
            break
        return [sample_msg_file_content,filename]
    except Exception as e:
        print("error : " + str(e))
        return ["",""]

def create_issues_target(target="",issueTitle="", issueDescription=""):
    repos = target_repos(user_input=target)
    output=[]
    for repoName in repos.keys():
        repoList = repos[repoName]
        print("Initiating creation of issues in Repos : ", repoList)
        for repo in repoList:
            result = create_an_issue(title=issueTitle,description=issueDescription, repo=str(repo))
            if(result == False):
                print("Error while creating the issue in :", repo)
            else:
                issue_url = result[1]
                output.append(issue_url)
                print("Issue created successfully :", result[1])
    return output

def parse_yml_file(fileContent=None):
    global allowed_inputs
    print("Inside parse_yml_file")
    if(fileContent ==  None):
        return False
    filedata = yaml.safe_load(fileContent)
    print("received file content : ", fileContent)
    print("loaded yml from the string", filedata)

    title = ""
    description = ""
    comments = ""
    recepient_type = ""
    operation = ""
    global gMessageId
    if("title" in filedata):
        title = filedata["title"]
    if("description" in filedata):
        description = filedata["description"]
    if("comments" in filedata):
        comments = filedata["comments"]
    if("recepient_type" in filedata):
        recepient_type = filedata["recepient_type"]
    if("issue_id_list" in filedata):
        issue_id_list = filedata["issue_id_list"]
    if("msg-id" in filedata):
        gMessageId = filedata["msg-id"]
    else:
        gMessageId = str(int(time.time())) + str(random.randint(0,MAX_RANDOM)) # Newly generated random id
    if("operation" in filedata):
        operation = filedata["operation"]
    else:
        # Exit if operation variable is not present
        print("Please pass the operation to be performed: create_issues/add_comments/close_issues")
        sys.exit()
    print("title:", title,"description:", description, "comments:", comments, "rec_type", recepient_type)
    
    if(recepient_type == None):
        #Close all issues
        pass
    elif(recepient_type == "all"):
        #Create issues in all repo (templates, image_stream)
        #create_issues_target(target="templates", issueTitle=title, issueDescription=description)
        #create_issues_target(target="image_streams", issueTitle=title, issueDescription=description)
        #output = target_repos(user_input=recepient_type, issueTitle=title, issueDescription=description)
        #output format : List([repo_name, issue_id_url])
        #print("[+] Executed in all")
        return output
    elif(recepient_type == "templates"):
        #Create issues in all the repo present under templates
        print("[+] Inside templates")
        output = target_repos(user_input=recepient_type, issueTitle=title, issueDescription=description)
        #output format : List([repo_name, issue_id_url])
        print("[+] Executed in templates")
        return output
    elif(recepient_type == "image_stream"):
        #Create issues in all the image_steram repo
        print("[+] Inside image_stream")
        output = target_repos(user_input=recepient_type, issueTitle=title, issueDescription=description)
        #output format : List([repo_name, issue_id_url])
        print("[+] Executed in image_stream")
        return output
    elif(recepient_type == "testimagestreams"):
        #Create issues in test image_streams
        print("[+] Inside testimagestreams")
        output = target_repos(user_input=recepient_type, issueTitle=title, issueDescription=description)
        #output format : List([repo_name, issue_id_url])
        print("[+] Executed in testimagesteams")
        return output
    elif(recepient_type == "testtemplates"):
        #Create issues in test templates
        print("[+] Inside testtemplates")
        if(operation == "create_issues"):
            #output = target_repos(user_input=recepient_type, issueTitle=title, issueDescription=description)
            output = create_issues_target(target="testtemplates", issueTitle=title, issueDescription=description)
            #output format : List([repo_name, issue_id_url])
            print("[+] Executed in testtemplates ")
            return output
    elif(recepient_type == "testall"):
        #Create issues in all test repos - image_stream and templates
        print("[+] Inside testall")
        output = target_repos(user_input=recepient_type, issueTitle=title, issueDescription=description)
        #output format : List([repo_name, issue_id_url])
        print("[+] Executed in testall")
        return output
    else:
        #Throw error
        pass

def update_message_file(pr_url="", filename="", filecontent=""):
    is_updated = update_file(filename=filename, content=filecontent)
    try:
        if(is_updated):
            print("Updates messaage file successfully!!")
        else:
            print("Could not update message file!!")   
    except Exception as e:
        print("Error while trying to update message file : " + str(e))

def update_state_file():
    pass



def main():
    '''
    Execution Steps:
    1. Load the yaml file to fetch all the repo - load_openshift_yml()
    2. Parse PR body. Check with necessary conditions.
    3. Once parsed, call the appropriate functions and execute the steps.
    '''
    # Uncomment below once in Production
    # load_openshift_yaml()
    # print("Loaded OpenShift yaml file")
    # Code block for sample message file
    [sample_msg_file_content, filename] = get_yaml_from_pr(pr_url=pr_url)
    if(sample_msg_file_content=="" or filename == ""):
        print("sample_msg_file_content : ", sample_msg_file_content)
        print("filename : ", filename)
        print("Unable to extract the content from PR.")
        print("Exiting now")
        sys.exit()
    #  Code block for state message file
    base_url = str(pr_url.split("/pulls")[0])
    state_msg_url_main = base_url + "/contents/state" + "/state-msg.yml?ref="+"main"
    state_file_content = read_yml_file(file_url=state_msg_url_main)
    if(state_file_content==""):
        print("state_msg_url_main : ", state_msg_url_main)
        print("state_file_content : ", sample_msg_file_content)
        print("Unable to extract the content from main branch.")
        print("Exiting now")
        sys.exit()
    msg_id_dict = yaml.safe_load(state_file_content)
    if(msg_id_dict == None):
        msg_id_dict = dict()



    
    # Parse the yaml content which we got from PR
    try:
        sample_msg_yml_format = yaml.safe_load(sample_msg_file_content)
    except Exception as e:
        print("Not valid yaml content")
        print("Exiting now")
        sys.exit()

    if("operation" not in sample_msg_yml_format):
        print("Operation not specified. Exiting Now")
        sys.exit()
    else:
        operation = sample_msg_yml_format["operation"]
        if(operation not in VALID_OPERATIONS):
            print("Invalid operation specified : " + str(operation) + ". Exiting Now!")
            sys.exit()
    if("recepient_type" not in sample_msg_yml_format):
        print("Recepient Type not found")
    else:
        recepient_type = sample_msg_yml_format["recepient_type"]
        if(recepient_type not in VALID_RECEPIENT_TYPE):
            print("Invalid recepient type : " + str(recepient_type) + ". Exiting Now!")
            sys.exit()
    
    # Once you reach here, you will have valid operation to perform on valid recepient_type
    if(operation == "create_issues"):
        if("title" not in sample_msg_yml_format):
            print("Could not find the title. Exiting Now!")
            sys.exit()
        elif("description" not in sample_msg_yml_format):
            print("Could not find the description. Exiting Now!")
            sys.exit()
        
        title = sample_msg_yml_format["title"]
        description = sample_msg_yml_format["description"]
        if(title == ""):
            print("Found empty title. Exiting Now!")
            sys.exit()
        if(description == ""):
            print("Found empty description. Exiting Now!")
            sys.exit()
        # Now, call create_issue(recepient_type="", title="", description=""). This will return [repo-url, issue-url]
        issue_dict = {}
        if(recepient_type == "testall"):
            issue_url_list = create_issues_target(target="testtemplates", issueTitle=title, issueDescription=description)
            issue_dict["testtemplates"] = issue_url_list
            issue_url_list = []
            issue_url_list = create_issues_target(target="testimagestreams", issueTitle=title, issueDescription=description)
            issue_dict["testimagestreams"] = issue_url_list
            issue_url_list = []
        elif(recepient_type == "testtemplates"):
            issue_url_list = create_issues_target(target="testtemplates", issueTitle=title, issueDescription=description)
            issue_dict["testtemplates"] = issue_url_list
            issue_url_list = []
        elif(recepient_type == "testimagestreams"):
            issue_url_list = create_issues_target(target="testimagestreams", issueTitle=title, issueDescription=description)
            issue_dict["testimagestreams"] = issue_url_list
            issue_url_list = []
        else:
            print("Could not find recepient_type. Exiting Now!")
            sys.exit()
        if(issue_dict == {}):
            print("Did not find any issues to update. Exiting Now!")
            sys.exit()
        
        # Now, we have to update sample-msg.yml with msg-id, and update state-msg.yml file with msg-id:issue-url
        if("msg-id" in sample_msg_yml_format):
            msg_id = sample_msg_yml_format["msg-id"]
            # No need to updatem sample-msg.yml file now
        else:
            msg_id = str(int(time.time()))
            # Now, append sample-msg.yml file
            sample_msg_file_content +="\nmsg-id: " + str(msg_id)
            print("Updating sample-msg.yml file")
            fileurl = str(pr_url.split("/pulls")[0]) + "/contents/" + str(filename) + "?ref=" + str(source_branch)
            print("File being udpated : " + str(fileurl))
            if(update_file(filename=fileurl, content=sample_msg_file_content)):
                print("Updated sample-msg.yml file successfully!")
            else:
                print("Could not update sample-msg.yml file. Exiting Now!")
                sys.exit()
        
        # Once you are here, sample-msg.yml file should be in correct format.
        # Now, update state-msg.yml file with msg-id and issue-url.
        state_msg_url = base_url + "/contents/state" + "/state-msg.yml?ref="+str(source_branch)
        print("URL generated for state file  : " + str(state_msg_url))
        headers = {'Accept': 'application/vnd.github.v3+json'}
        #state_file_content = requests.get(state_msg_url, headers=headers).text
        if(msg_id not in msg_id_dict):
            msg_id_dict[msg_id] = dict()
            print("[-] Provided message id not found. Added new message id.")
        for key in issue_dict:
            if(key in msg_id_dict[msg_id]):
                msg_id_dict[msg_id][key].append(issue_dict[key])
            else:
                msg_id_dict[msg_id][key] = [issue_dict[key]]
        print("[+] Issues added to msg_id_dict")
        print("[+] msg_id_dict : ", msg_id_dict)
        print("[+] Generating the content for state_msg_file")
        state_file_content = ""
        for key in msg_id_dict.keys():
            state_file_content += str(msg_id) + ":"
            for key in issue_dict:
                state_file_content += "\n" + " " + str(key)
                issues_list = issue_dict[key]
                for issue in issues_list:
                    state_file_content += "\n" + " " + " " + "- " + str(issue)
            state_file_content += "\n"
        print("state_msg_file content generated", state_file_content)
        if(update_file(filename=state_msg_url, content=state_file_content)):
            print("Updated state-msg.yml file")
        else:
            print("Unable to updaet state-msg.yml file")
        print("[+] Initiating the merge of pull request")
        print("[+] Sleeping for 5 sec to ensure commits are updated.")
        time.sleep(5)
        isMerged = merge_pull_request(pr_url=pr_url, commit_title=PR_MERGE_COMMIT_TITLE, commit_message=PR_MERGE_COMMIT_MESSAGE)
        if(isMerged):
            print("[+] Merge successfull!")
        else:
            print("[-] Could not merge the request.")
    elif(operation == "close_issues"):
        pass
    elif(operation == "comment"):
        pass
    else:
        print("Could not find operation " + str(operation)+ ". Exiting Now!")
        sys.exit()


    #update_message_file(pr_url=pr_url, filename=file_url, filecontent=file_content)
    
    
    '''
    # 1. Update sample-msg.yml file
    print("Starting to update sample-msg.yml file")
    file_url = str(pr_url.split("/pulls")[0]) + "/contents/" + str(yml_file) + "?ref=" + str(source_branch)
    file_content += "\nmsg-id: " + str(gMessageId)
    update_message_file(pr_url=pr_url, filename=file_url, filecontent=file_content)
    print("Updated sample-msg.yml file")

    
    # 2. Update state-msg.yml file
    final_file_content = "msg-id: " + str(gMessageId)
    print("Starting to update state-msg.yml file")
    outputs = parse_yml_file(fileContent=file_content) #Format List([repo-url, issue-list])
    base_url = str(pr_url.split("/pulls")[0])
    state_msg_url = base_url + "/state" + "/state-msg.yml?ref=main"
    print("state_msg_url : " + str(state_msg_url))
    for output in outputs:
        repo_url, issue_url, target = output[0],output[1], output[2]
        final_file_content += f""" {target} - {repo_url} : {issue_url}\n"""
    
    #update_state_file(pr_url=pr_url, issue_url)
    final_file_content_yml = yaml.safe_load(final_file_content)
    update_file(filename=state_msg_url, filecontent=final_file_content_yml)
    print("Finished updating state-msg.yml file")
    '''
    
    

# File execution strats from here
main()