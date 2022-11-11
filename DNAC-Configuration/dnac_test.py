from dnacentersdk import DNACenterAPI
from dnacentersdk.exceptions import ApiError
import requests
from requests.auth import HTTPBasicAuth
import json
import time

DNAC_URL = "https://198.18.133.101:443"
DNAC_USER = "admin"
DNAC_PASS = "C1sco12345"
DNAC_AUTH = HTTPBasicAuth(DNAC_USER, DNAC_PASS)
DEBUG = False

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
    fabric_site_payload = {
        "siteNameHierarchy": site_hierarchy
    }
    url = DNAC_URL + '/dna/intent/api/v1/business/sda/fabric-site'
    header = {'content-type': 'application/json', 'x-auth-token': dnac_token}
    response = requests.post(url, data=json.dumps(fabric_site_payload), headers=header, verify=False)
    response_json = response.json()
    return response_json

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
    try:
        response = dnac_api.sites.create_site(payload=area_payload)
    except ApiError as e:
        print(e)
    time_sleep(5)
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
    try:
        response = dnac_api.sites.create_site(payload=building_payload)
    except ApiError as e:
        print(e)
    time_sleep(5)
    return response

    return response

def create_floor(floor_name, parent, number, dnac_api):
    # create a new floor
    floor_payload = {
        'type': 'floor',
        'site': {
            'floor': {
                'name': floor_name,
                'number': number,
                'parentName': parent,
                "rfModel": "Cubes And Walled Offices"
            }
        }
    }
    try:
        response = dnac_api.sites.create_site(payload=floor_payload)
    except ApiError as e:
        print(e)
    time_sleep(3)
    if (DEBUG):
        print(floor_payload)
        print(response)
    return response

def create_vn(l3_vn_name, dnac_api):
    # create L3 VN at global level
    l3_vn_payload = {
        'virtualNetworkName': l3_vn_name,
        "isGuestVirtualNetwork": False,
    }
    try:
        response = dnac_api.sda.add_virtual_network_with_scalable_groups(payload=l3_vn_payload)
    except ApiError as e:
        print(e)
    if (DEBUG):
        print(l3_vn_payload)
        print(response)
    return response
    time_sleep(5)

# Create a DNACenterAPI "Connection Object"
dnac_api = DNACenterAPI(username=DNAC_USER, password=DNAC_PASS, base_url=DNAC_URL, version='2.2.2.3', verify=False)
# get Cisco DNA Center Auth token
dnac_auth = get_dnac_token(DNAC_AUTH)
auth = get_auth_token(DNAC_URL, DNAC_USER, DNAC_PASS)

# open json file
json_handle = json.loads(open("DNAC-Configuration/sd-fabric.json").read())

print("Configuring DNAC from sd-fabric.json .....")
print("------------------------------------------------------------")

#
# cycle through all vrfs defined in json
#
for x in json_handle['vrfs']:
    print(" Creating VRF         : " + x["name"])
    create_vn(x["name"], dnac_api)
#
# cycle through all areas defined in json
#
for x in json_handle['areas']:
    #
    # set the site_hierarchy path, if this isn't Global root then add Global/ in front
    #
    site_hierarchy = str(x['parent']) + "/" + str(x['area'])
    if (str(x['parent']) != "Global"):
        site_hierarchy = "Global/" + str(x['parent']) + "/" + str(x['area'])
    print(" Creating Area        : " + site_hierarchy)
    create_area(x['area'], x['parent'], dnac_api)
    #
    # if this is a fabric site then create one
    # we should assign vn's to fabric after creating it
    #
    if (x['fabric_site'] == "True"):
        print(" Creating Fabric Site : " + site_hierarchy)
        create_fabric_site(site_hierarchy, auth["token"])
    #
    # cycle though any defined buildings and add
    #
    for building in (x['buildings']):
        building_hierarchy = site_hierarchy + "/" + str(building['name'])
        print(" Creating Building    : " + building_hierarchy)
        create_building(str(building['name']), site_hierarchy, building['address'], dnac_api)
        #
        # cycle though any defined floors for this building
        #
        for floor in (building['floors']):
            floor_hierarchy = building_hierarchy + "/" + str(floor['name'])
            print(" Creating Floor       : " + floor_hierarchy)
            create_floor(str(floor['name']), building_hierarchy, floor['number'], dnac_api)





