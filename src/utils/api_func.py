import os
import json
import requests

def nums_of_total_pages():
    params = {
        'sort': 'createdAt;asc',
        'page': 0,
        'size': 200
    }
    response = requests.get('https://dev.api.commonground.tw/api/issues', params=params)
    return response.json()['page']['totalPage']

def get_all_issue_ids():
    total_pages = nums_of_total_pages()
    all_issue_ids = []
    for i in range(total_pages):
        params = {
            'sort': 'createdAt;asc',
            'page': i,
            'size': 200
        }
        response = requests.get('https://dev.api.commonground.tw/api/issues', params=params)
        for issue in response.json()['content']:
            all_issue_ids.append(issue['id'])
    return all_issue_ids

def load_viewspoints_from_issue_id(issue_id):
    params = {
        'sort': 'createdAt;asc',
        'size': 200,
        'page': 0
    }
    url = f"https://dev.api.commonground.tw/api/issue/{issue_id}/viewpoints"
    response = requests.get(url, params=params)
    totalPage = response.json()['page']['totalPage']
    contents = {}
    contents['content'] = []
    for i in range(totalPage):
        params['page'] = i
        response = requests.get(url, params=params)
        for viewpoint in response.json()['content']:
            contents['content'].append(viewpoint)
    return contents
   
