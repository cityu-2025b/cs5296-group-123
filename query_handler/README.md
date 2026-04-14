# Query Handler API

Two endpoints are exposed through API Gateway:

- GET /text-search
- POST /search-image

Base URL: https://abn57op5z4.execute-api.us-east-1.amazonaws.com/prod

## 1) Text Search

Endpoint: GET /text-search

Query parameters:

- inputText (required): search text
- size (optional): positive integer, default is 10

Example:

```bash
curl -G 'https://abn57op5z4.execute-api.us-east-1.amazonaws.com/prod/text-search' \
  --data-urlencode 'inputText=red compact suv alloy wheels' \
  --data-urlencode 'size=5'
```

Success response (200):

```json
[
  {
    "_index": "cs5296-index",
    "_id": "sample-1",
    "_score": 0.65,
    "_source": {
      "description": "Volvo XC40 compact SUV red alloy wheels clean condition front-three-quarter view"
    }
  }
]
```

Validation errors:

- inputText is required
- size must be an integer
- size must be greater than 0

## 2) Image Search

Endpoint: POST /search-image

Request JSON body:

- image (required): base64 image string
- size (optional): positive integer (currently the backend defaults to 5)

Important: the required JSON key is image, not image_data.

Example:

```bash
IMG='dev-image-descriptor/image/Volvo_088.jpg'
B64=$(base64 < "$IMG" | tr -d '\n')
curl -X POST 'https://abn57op5z4.execute-api.us-east-1.amazonaws.com/prod/search-image' \
  -H 'Content-Type: application/json' \
  -d "{\"image\":\"$B64\",\"size\":5}"
```

Success response (200):

```json
[
  {
    "_index": "cs5296-index",
    "_id": "sample-1",
    "_score": 1.04,
    "_source": {
      "description": "Volvo XC40 compact SUV red alloy wheels clean condition front-three-quarter view"
    }
  }
]
```

Validation errors:

- Image is required

## 3) Direct Browser (Vanilla JavaScript)

Ready-made page in this repo:

- browser-demo.html

Quick open (from query_handler directory):

```bash
python3 -m http.server 8080
```

Then visit:

- http://localhost:8080/browser-demo.html

If you start the server from the repo root instead, use:

```bash
python3 -m http.server 8080 --directory query_handler
```

Then visit the same URL above. If you started a server from repo root without `--directory query_handler`, use:

- http://localhost:8080/query_handler/browser-demo.html

If your browser blocks local file fetches, use the local server above instead of opening the HTML file directly.

## 4) OpenAPI File

See openapi.yaml for a machine-readable contract that frontend code generators can use.
