import json
json = json.loads(open('sd-fabric.json').read())

print (type(json['areas']))

for x in json['areas']:
    print(str(x['parent']) + "/" + x['area'])
