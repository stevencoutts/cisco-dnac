import os
from dotenv import load_dotenv
from pathlib import Path
from dnacentersdk import api
import requests
from requests.auth import HTTPBasicAuth
import json

load_dotenv()
env_path = Path('.')/''
load_dotenv(dotenv_path=env_path)
print(env_path)
print (os.getenv("DNAC_URL"))
DNAC_URL = "https://sandboxdnac2.cisco.com:443"
DNAC_USER = "devnetuser"
DNAC_PASS = "Cisco123!"

def get_auth_token(DNAC_URL, DNAC_USER, DNAC_PASS):
    """ Authenticates with controller and returns a token to be used in subsequent API invocations
    """
    login_url = DNAC_URL+"/api/system/v1/auth/token"
    print(login_url)
    result = requests.post(url=login_url, auth=HTTPBasicAuth(DNAC_USER, DNAC_PASS), verify=False)
    result.raise_for_status()

    token = result.json()["Token"]
    return {
        "token": token
    }

def create_fabric_site(site_hierarchy, dnac_token):
    """
    This function will create a new fabric at the site with the hierarchy {site_hierarchy}
    :param site_hierarchy: site hierarchy, for example {Global/OR/PDX-1/Floor-2}
    :param dnac_token: Cisco DNA Center auth token
    :return: response in JSON
    """
    payload = {
        "siteNameHierarchy": site_hierarchy
    }
    url = DNAC_URL + '/dna/intent/api/v1/business/sda/fabric-site'
    header = {'content-type': 'application/json', 'x-auth-token': dnac_token}
    response = requests.post(url, data=json.dumps(payload), headers=header, verify=False)
    response_json = response.json()
    print (response_json)

auth = get_auth_token(DNAC_URL, DNAC_USER, DNAC_PASS)
print(auth["token"])
create_fabric_site("XMA", auth["token"])



