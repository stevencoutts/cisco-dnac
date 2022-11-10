from dnacentersdk import DNACenterAPI
import requests
from requests.auth import HTTPBasicAuth
import json
import time

DNAC_URL = "https://198.18.133.101:443"
DNAC_USER = "admin"
DNAC_PASS = "C1sco12345"
DNAC_AUTH = HTTPBasicAuth(DNAC_USER, DNAC_PASS)

def time_sleep(time_sec):
    """
    This function will wait for the specified time_sec, while printing a progress bar, one '!' / second
    Sample Output :
    Wait for 10 seconds
    !!!!!!!!!!
    :param time_sec: time, in seconds
    :return: none
    """
    for i in range(time_sec):
        #print('!', end='')
        time.sleep(1)
    return

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
    response = requests.post(url, data=payload, headers=header, verify=False)
    return response

def create_area(name, parent, dnac_api):
    # create a new area
    area_payload = {
        "type": "area",
        "site": {
            "area": {
                "name": name,
                "parentName": parent
            }
        }
    }
    response = dnac_api.sites.create_site(payload=area_payload)
    time_sleep(10)
    return response

def create_building(name, parent, postcode, dnac_api):
    building_payload = {
        'type': 'building',
        'site': {
            'building': {
                'name': name,
                'parentName': parent,
                'address': postcode
            }
        }
    }
    response = dnac_api.sites.create_site(payload=building_payload)
    time_sleep(10)
    return response

# Create a DNACenterAPI "Connection Object"
dnac_api = DNACenterAPI(username=DNAC_USER, password=DNAC_PASS, base_url=DNAC_URL, version='2.2.2.3', verify=False)
# get Cisco DNA Center Auth token
dnac_auth = get_dnac_token(DNAC_AUTH)

auth = get_auth_token(DNAC_URL, DNAC_USER, DNAC_PASS)

#create_area("Manchester", "Global", dnac_api)
#create_area("Data Centre", "Manchester", dnac_api)
#create_building("DC 1", "Global/Manchester/Data Centre", "SR3 2NY", dnac_api)
#create_building("DC 2", "Global/Manchester/Data Centre", "SR3 2TT", dnac_api)
#create_fabric_site("Global/Manchester/Data Centre", auth["token"])
#create_area("Test Building", "Manchester", dnac_api)
#create_fabric_site("Global/Manchester/Test Building", auth["token"])

json = json.loads(open("DNAC-Configuration/sd-fabric.json").read())

print (type(json['areas']))

for x in json['areas']:
    site_hierarchy = "Global/" + str(x['parent']) + "/" + str(x['area'])
    print(" Creating Area        : " + str(x['parent']) + "/" + x['area'])
    create_area(x['area'], x['parent'], dnac_api)
    if (x['fabric_site'] == "True"):
        print(" Creating Fabric Site : " + site_hierarchy)
        create_fabric_site(site_hierarchy, auth["token"])
    for y in (x['buildings']):
        print(" Creating Building    : " + str(y['name']))
        create_building(y['name'], site_hierarchy, y['address'], dnac_api)









