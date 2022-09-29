import json
import logging
import os
import requests
from authlib.integrations.requests_client import OAuth2Session

def _get_jwt_token(auth_url: str = None):
    """Connect to the server and get a JWT token."""

    if auth_url == None:
      auth_url = "https://vectara-prod-{}.auth.us-west-2.amazoncognito.com".format(os.environ.get('VECTARA_CUSTOMER_ID'))

    token_endpoint = f"{auth_url}/oauth2/token"
    session = OAuth2Session(
        os.environ.get('VECTARA_APP_ID'), os.environ.get('VECTARA_APP_SECRET'), scope="")
    token = session.fetch_token(token_endpoint, grant_type="client_credentials")
    return token["access_token"]


def search_raw(headers: dict, data: dict):
    """ Takes headers and the JSON body and performs a search against Vectara """
    payload = json.dumps(data)
    
    response = requests.post(
        "https://h.serving.vectara.io/v1/query",
        data=payload,
        verify=True,
        headers=headers)
    search_results = json.loads(response.content)
    return data, search_results

def search(search_text: str, rerank: bool, num_results: int, metadata_filters: dict = None):
    """ Takes headers and the JSON body and performs a search against Vectara """
    jwt_token = _get_jwt_token()
    api_key_header = {
        "Authorization": f"Bearer {jwt_token}",
        "customer-id": os.environ.get('VECTARA_CUSTOMER_ID')
    }
    data_dict = {
        "query": [
            {
                "query": search_text,
                "num_results": num_results,
                "corpus_key": [
                    {
                        "customer_id": int(os.environ.get('VECTARA_CUSTOMER_ID')),
                        "corpus_id": int(os.environ.get('VECTARA_CORPUS_ID'))
                    }
                ]
            }
        ]
    }
    if rerank == True:
        data_dict['query'][0]['rerankingConfig'] = { "reranker_id": 272725717 }
        data_dict['query'][0]['start'] = 0
        data_dict['query'][0]['num_results'] = 100
    if metadata_filters != None:
        filter_string = " AND ".join(metadata_filters)
        data_dict['query'][0]['corpus_key'][0]['metadata_filter'] = filter_string
    return search_raw(api_key_header, data_dict)

def index_message(customer_id: int, corpus_id: int, text: str,
                  id: str, title: str, metadata: dict = None,
                  idx_address: str = "indexing.vectara.io"):
    """ Indexes a document to Vectara """
    jwt_token = _get_jwt_token()
    post_headers = {
        "Authorization": f"Bearer {jwt_token}",
        "customer-id": f"{customer_id}"
    }

    document = {}
    document["document_id"] = id
    # Note that the document ID must be unique for a given corpus
    document["title"] = title
    document["metadata_json"] = json.dumps(metadata)
    sections = []
    section = {}
    section["text"] = text
    sections.append(section)
    document["section"] = sections

    request = {}
    request['customer_id'] = customer_id
    request['corpus_id'] = corpus_id
    request['document'] = document

    response = requests.post(
        f"https://h.{idx_address}/v1/index",
        data=json.dumps(request),
        verify=True,
        headers=post_headers)

    if response.status_code != 200:
        logging.error("REST upload failed with code %d, reason %s, text %s",
                       response.status_code,
                       response.reason,
                       response.text)
        return response, False
    return response, True

def get_metadata_value(document_metadata, metadata_name):
  """ This function takes the name of metadata and returns its value or 'Unknown' """
  val = None
  try:
    val = list(filter(lambda x: x['name'] == metadata_name, document_metadata))[0]['value']
  except:
    val = "Unknown"
  return val