import json
json = json.loads(open('sample.json').read())

print (type(json['areas']))

for x in json['areas']:
    print(x)
