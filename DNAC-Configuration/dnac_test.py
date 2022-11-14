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
DEBUG = True

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
        print(json.dumps(floor_payload, indent=4))
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

def assign_l3_vn(l3_vn_name, site_hierarchy, dnac_token):
    """
    This function will create a new L3 virtual network with the name {l3_vn_name} at the site
    with the hierarchy {site_hierarchy}
    :param l3_vn_name: L3 VN name
    :param site_hierarchy: site hierarchy
    :param dnac_token: Cisco DNA Center auth token
    :return: API response
    """
    url = DNAC_URL + '/dna/intent/api/v1/business/sda/virtual-network'
    payload = {
        'virtualNetworkName': l3_vn_name,
        "siteNameHierarchy": site_hierarchy
    }
    header = {'content-type': 'application/json', 'x-auth-token': dnac_token}
    response = requests.post(url, data=json.dumps(payload), headers=header, verify=False)
    response_json = response.json()
    return response_json

def set_network_settings(domain, dns1, dns2, ntpServer, dhcpServer, timezone, dnac_api):
    # create site network settings
    network_settings_payload = {
        'settings': {
            'dnsServer': {
                'domainName': domain,
                'primaryIpAddress': dns1,
                'secondaryIpAddress': dns2
            },
            'ntpServer': ntpServer,
            'dhcpServer': dhcpServer,
            'timezone': timezone
        }
    }
    # get the site_id
    response = dnac_api.sites.get_site(name='Global')
    site_id = response['response'][0]['id']
    try:
        response = dnac_api.network_settings.create_network(site_id=site_id, payload=network_settings_payload)
    except ApiError as e:
        print(e)
    time_sleep(3)
    if (DEBUG):
        print(json.dumps(network_settings_payload, indent=4))
        print(response)
    time_sleep(10)
    return response

def create_auth_profile(auth_profile, site_hierarchy, dnac_token):
    """
    This function will create a new default auth profile for the fabric at the {site_hierarchy}
    :param auth_profile: auth profile, enum { No Authentication , Open Authentication, Closed Authentication, Low Impact}
    :param site_hierarchy: site hierarchy
    :param dnac_token: Cisco DNA Center auth token
    :return: API response
    """
    url = DNAC_URL + '/dna/intent/api/v1/business/sda/authentication-profile'
    payload = {
        'siteNameHierarchy': site_hierarchy,
        "authenticateTemplateName": auth_profile
    }
    header = {'content-type': 'application/json', 'x-auth-token': dnac_token}
    response = requests.post(url, data=json.dumps(payload), headers=header, verify=False)
    response_json = response.json()
    return response_json

def create_global_ippool(ip_pool_name, ip_pool_address_space, ip_pool_cidr):
    # create a new Global Pool
    global_pool_payload = {
        'settings': {
            'ippool': [
                {
                    'ipPoolName': ip_pool_name,
                    'type': "Generic",
                    'ipPoolCidr': ip_pool_cidr,
                    'IpAddressSpace': ip_pool_address_space
                }
            ]
        }
    }
    try:
        response = dnac_api.network_settings.create_global_pool(payload=global_pool_payload)
    except ApiError as e:
        print(e)
    time_sleep(3)
    if (DEBUG):
        print(json.dumps(global_pool_payload, indent=4))
        print(response)
    return response

def reserve_ip_pool(hierarchy, subnet, prefix, parent, name):
    response = dnac_api.sites.get_site(name=hierarchy)
    site_id = response['response'][0]['id']
    # create an IP sub_pool for site_hierarchy
    #ip_sub_pool_subnet = ip_sub_pool_cidr.split('/')[0]
    #ip_sub_pool_mask = int(ip_sub_pool_cidr.split('/')[1])
    sub_pool_payload = {
        'name': name,
        'type': 'Generic',
        'ipv4GlobalPool': parent,
        'ipv4Prefix': True,
        'ipv6AddressSpace': False,
        'ipv4PrefixLength': prefix,
        'ipv4Subnet': subnet
    }
    try:
        response = dnac_api.network_settings.reserve_ip_subpool(site_id=site_id, payload=sub_pool_payload)
    except ApiError as e:
        print(e)
    time_sleep(3)
    if (DEBUG):
        print(json.dumps(sub_pool_payload, indent=4))
        print(response)
    return response

# Create a DNACenterAPI "Connection Object"
dnac_api = DNACenterAPI(username=DNAC_USER, password=DNAC_PASS, base_url=DNAC_URL, version='2.2.2.3', verify=False)
# get Cisco DNA Center Auth token
dnac_auth = get_dnac_token(DNAC_AUTH)
auth = get_auth_token(DNAC_URL, DNAC_USER, DNAC_PASS)

# open json file
json_handle = json.loads(open("DNAC-Configuration/working.json").read())

print("Configuring DNAC from sd-fabric.json .....")
print("------------------------------------------------------------")

#
# cycle through all vrfs defined in json
#
for x in json_handle['vrfs']:
    print(" Creating VRF         : " + x["name"])
    create_vn(x["name"], dnac_api)
#
# cycle through all network settings and configure as global
#
for x in json_handle['network-settings']:
    print(" Net Settings DNS     : " + x["dns1"] + ", " + x["dns2"])
    print("                      : " + x["domain"])
    print(" Net Settings NTP     : " + str(x["ntpServer"]))
    print("                      : " + x["timezone"])
    print(" Net Settings DHCP    : " + str(x["dhcpServer"]))
    set_network_settings(x['domain'], x['dns1'], x['dns2'], x["dhcpServer"], x["ntpServer"], x["timezone"], dnac_api)
#
# cycle through all global IP pools
#
for x in json_handle['global-ip-pools']:
    print(" Global IP Pool       : " + x["name"] + ", " + x["subnet"] + x["cidr"])
    create_global_ippool(x["name"], x["subnet"], x["subnet"] + x["cidr"])
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
    # cycle though any defined IP Pools for this area
    #
    for ippool in (x['reserved-ip-pools']):
        print(" Reserving IP Pool    : " + site_hierarchy + ", " + ippool["name"])
        reserve_ip_pool(site_hierarchy, ippool["subnet"], ippool["cidr"], ippool["parent"], ippool["name"])

    #
    # if this is a fabric site then create one
    #
    if (x['fabric_site'] == "True"):
        print(" Creating Fabric Site : " + site_hierarchy)
        create_fabric_site(site_hierarchy, auth["token"])
        #
        # cycle through all vrfs defined in json
        # assign the vrf to this fabric site
        #
        for vrf in json_handle['vrfs']:
            print(" Assigning VRF        : " + site_hierarchy + "/" + vrf["name"])
            assign_l3_vn(vrf["name"], site_hierarchy, auth["token"])
        #
        # also assign INFRA_VN
        #
        print(" Assigning VRF        : " + site_hierarchy + "/INFRA_VN")
        assign_l3_vn("INFRA_VN", site_hierarchy, auth["token"])
        #
        # Set the default authentication template
        #
        print(" Set Auth Template    : " + site_hierarchy + " - No Authentication")
        create_auth_profile("No Authentication", site_hierarchy, auth["token"])
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




