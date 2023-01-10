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
import uuid

parser = argparse.ArgumentParser()
parser.add_argument("--pr_url", help="Name of the yaml file which triggered this action")
parser.add_argument("--branch", help="Source branch from where PR is generated")
args = parser.parse_args()

pr_url = args.pr_url
source_branch = args.branch
print("Received Data: ", pr_url)
gFilename = "" # This will be used whie updating the issue.
gMessageId = "" # This variable will store the message id (either newly generated or previously generated)

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


def load_yaml():
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
    

def get_file_content_from_pr(pr_url=""):
    try:
        global gFileName
        pr_file_url = pr_url + "/files"
        headers = {'Accept': 'application/vnd.github.v3+json'}
        pr_files = requests.get(pr_file_url, headers=headers)
        files = pr_files.json()
        print("pr in get_file_content_from_pr : ", pr_url)
        print("Files : ", files)
        file_content = ""
        for file in files:
            filename = file["filename"]
            validFile = filename.startswith("message/") and filename.endswith(".yml")
            if(not validFile):
                continue
            raw_url = file['raw_url']
            gFilename = filename
            print("Global Variable Set: ", gFilename)
            file_content = requests.get(raw_url, headers=headers).text
            print("File Content : ", file_content)
            break
        return [file_content,filename]
    except Exception as e:
        print("error : " + str(e))
        return False

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
                repo_url = repoList[0]
                issue_url = result[1]
                output.append([repo_url, issue_url, target])
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
        gMessageId = uuid.uuid4() # Newly generated random id
    if("operation" in filedata):
        operation = filedata["operation"]
    else:
        # Exit if operation variable is not present
        print("Please pass the operation to be performed: create_issues/add_comments/close_issues")
        sys.exit()
    print("title:", title,"description:", description, "comments:", comments, "rec_type", recepient_type)
    if(recepient_type in allowed_inputs):
        load_yaml()
    else:
        print("Invalid recepient type")
        sys.exit()
    print("loaded main yml file")
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
        #output = target_repos(user_input=recepient_type, issueTitle=title, issueDescription=description)
        output = create_issues_target(target="testtemplates", issueTitle=title, issueDescription=description)
        #output format : List([repo_name, issue_id_url])
        print("[+] Executed in testtemplates")
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
    1. Load the yaml file to fetch all the repo - load_yml()
    2. Parse PR body. Check with necessary conditions.
    3. Once parsed, call the appropriate functions and execute the steps.
    '''
    temp = get_file_content_from_pr(pr_url=pr_url)
    if(temp == False):
        print("Error while fetching content from the PR")
        sys.exit()
    file_content = temp[0]
    yml_file = temp[1]
    print("File Content : ", file_content)
    print("Calling the parse_yml_file function")
    
    #update_message_file(pr_url=pr_url, filename=file_url, filecontent=file_content)
    
    
    
    # 1. Update sample-msg.yml file
    print("Starting to update sample-msg.yml file")
    file_url = str(pr_url.split("/pulls")[0]) + "/contents/" + str(yml_file) + "?ref=" + str(source_branch)
    file_content += "msg-id: " + str(gMessageId)
    update_message_file(pr_url=pr_url, filename=file_url, filecontent=file_content)
    print("Updated sample-msg.yml file")

    '''
    # 2. Update state-msg.yml file
    print("Starting to update state-msg.yml file")
    outputs = parse_yml_file(fileContent=file_content) #Format List([repo-url, issue-list])
    base_url = str(pr_url.split("/pulls")[0])
    state_msg_url = base_url + "/state" + "/state-msg.yml?ref=main"
    for output in outputs:
        repo_url, issue_url, target = output[0],output[1], output[2]
        final_file_content += f""" {target} - {repo_url} : {issue_url}\n"""
    
    #update_state_file(pr_url=pr_url, issue_url)
    final_file_content_yml = yaml.safe_load(final_file_content)
    update_message_file(filename=state_msg_url, filecontent=final_file_content_yml)
    print("Finished updating state-msg.yml file")
    '''
    

# File execution strats from here
main()