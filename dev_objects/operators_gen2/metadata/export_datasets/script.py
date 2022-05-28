# Mock apis needs to be commented before used within SAP Data Intelligence
from diadmin.dimockapi.mock_api import api

import os
from urllib.parse import urljoin
import urllib
import json

import requests


#
#  GET Datasets
#
def get_datasets(connection, connection_id, container_name):
    api.logger.info(f"Get container of {container_name}")
    container_name = urllib.parse.quote(container_name, safe='')
    restapi = f"/catalog/connections/{connection_id}/containers/{container_name}"
    url = connection['url'] + restapi
    headers = {'X-Requested-With': 'XMLHttpRequest'}
    r = requests.get(url, headers=headers, auth=connection['auth'])

    if r.status_code != 200:
        api.logger.error(f"Status code: {r.status_code}  - {r.text}")
        return -1

    return json.loads(r.text)['datasets']


#
#  GET Tags of datasets
#
def get_dataset_tags(connection, dataset_path, connection_id=None, tag_hierarchies=None):
    path_list = dataset_path.strip('/').split("/")
    if not connection_id or connection_id == path_list[0]:
        connection_id = path_list[0]
        qualified_name = '/' + '/'.join(path_list[1:])
    else:
        qualified_name = '/' + '/'.join(path_list[0:])

    qualified_name = urllib.parse.quote(qualified_name, safe='')
    restapi = f"/catalog/connections/{connection_id}/datasets/{qualified_name}/tags"
    url = connection['url'] + restapi
    api.logger.info(f'Get Dataset Tags for: {dataset_path} ({connection_id})')
    headers = {'X-Requested-With': 'XMLHttpRequest'}
    params = {"connectionId": connection_id, "qualifiedName": dataset_path, 'tagHierarchies': tag_hierarchies}
    r = requests.get(url, headers=headers, auth=connection['auth'], params=params)

    if r.status_code != 200:
        api.logger.error(
            f"Get datasets attributes unsuccessful for {dataset_path}: {r.status_code}\n{json.loads(r.text)}")
        return None
    return json.loads(r.text)


#
# Callback of operator
#
def gen():
    host = api.config.http_connection['connectionProperties']['host']
    user = api.config.http_connection['connectionProperties']['user']
    pwd = api.config.http_connection['connectionProperties']['password']
    path = api.config.http_connection['connectionProperties']['path']
    tenant = os.environ.get('VSYSTEM_TENANT')

    if not tenant:
        tenant = 'default'

    connection = {'url': urljoin(host, path), 'auth': (tenant + '\\' + user, pwd)}

    datasets = get_datasets(connection, connection_id=api.config.connection_id, container_name=api.config.container)
    for i, dataset in enumerate(datasets):
        q_name = dataset['remoteObjectReference']['qualifiedName']
        dataset['tags'] = get_dataset_tags(connection, q_name, connection_id=api.config.connection_id)
        if api.config.streaming:
            if i == len(datasets)-1:
                header = [i, True, i + 1, len(datasets), ""]
            else:
                header = [i, False, i+1, len(datasets), ""]
            header = {"com.sap.headers.batch": header}
            datasets_json = json.dumps(dataset, indent=4)
            api.outputs.datasets.publish(datasets_json, header=header)

    if not api.config.streaming:
        header = [0, True, 1, 0, ""]
        header = {"com.sap.headers.batch": header}
        datasets_json = json.dumps(datasets, indent=4)
        api.outputs.datasets.publish(datasets_json, header=header)


api.set_prestart(gen)
