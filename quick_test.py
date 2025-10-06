import requests
query = {"query": '{ Get { DocumentChunk(limit: 3) { text file_name } } }'}
response = requests.post("http://localhost:8080/v1/graphql", json=query)
print(response.json())