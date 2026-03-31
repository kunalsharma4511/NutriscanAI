import urllib.request
import json
import pprint

from urllib.request import Request, urlopen

product_code = '8901058000269'
api_key = 'GOUPC_API_KEY'

req = Request('https://go-upc.com/api/v1/code/' + product_code)
req.add_header('Authorization', 'Bearer ' + api_key)

content = urlopen(req).read()
data = json.loads(content.decode())

product_name = data["product"]["name"]
product_description = data["product"]["description"]
product_image = data["product"]["imageUrl"]

print("Product Name: " + product_name + "\n")
print("Product Description: " + product_description + "\n")
print("Product Image URL: " + product_image + "\n")