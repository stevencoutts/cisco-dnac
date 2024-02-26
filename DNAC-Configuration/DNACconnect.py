from dnacentersdk import DNACenterAPI
from dnacentersdk.exceptions import ApiError
import requests
from requests.auth import HTTPBasicAuth

DNAC_URL = "https://sandboxdnac2.cisco.com:443"
DNAC_USER = "devnetuser"
DNAC_PASS = "Cisco123!"
DNAC_AUTH = HTTPBasicAuth(DNAC_USER, DNAC_PASS)

# Create a DNACenterAPI "Connection Object"
dnac_api = DNACenterAPI(username=DNAC_USER, password=DNAC_PASS, base_url=DNAC_URL, version='2.3.3.0', verify=False)

""""
Create the authorization token required to access Cisco DNA Center
Call to Cisco DNA Center - /api/system/v1/auth/login
:param dnac_auth - Cisco DNA Center Basic Auth string
"""
url = DNAC_URL + '/dna/system/api/v1/auth/token'
header = {'content-type': 'application/json'}
response = requests.post(url, auth=DNAC_AUTH, headers=header, verify=False)
response_json = response.json()
dnac_jwt_token = response_json['Token']

""" Authenticates with controller and returns a token to be used in subsequent API invocations
"""
login_url = DNAC_URL+"/api/system/v1/auth/token"
result = requests.post(url=login_url, auth=HTTPBasicAuth(DNAC_USER, DNAC_PASS), verify=False)
result.raise_for_status()

token = result.json()["Token"]







def get_dnac_token(dnac_auth):
    """
    Create the authorization token required to access Cisco DNA Center
    Call to Cisco DNA Center - /api/system/v1/auth/login
    :param dnac_auth - Cisco DNA Center Basic Auth string
    :return Cisco DNA Center Token
    """
    url = DNAC_URL + '/dna/system/api/v1/auth/token'
    header = {'content-type': 'application/json'}
    response = requests.post(url, auth=dnac_auth, headers=header, verify=False)
    response_json = response.json()
    dnac_jwt_token = response_json['Token']
    return dnac_jwt_token

def get_auth_token(DNAC_URL, DNAC_USER, DNAC_PASS):
    """ Authenticates with controller and returns a token to be used in subsequent API invocations
    """
    login_url = DNAC_URL+"/api/system/v1/auth/token"
    result = requests.post(url=login_url, auth=HTTPBasicAuth(DNAC_USER, DNAC_PASS), verify=False)
    result.raise_for_status()

    token = result.json()["Token"]
    return {
        "token": token
    }