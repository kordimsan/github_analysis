import sys
import requests
import collections
from datetime import datetime
from pprint import pprint

class graphQL:
  TOKEN = 'token 4e0ff38d1dd74628b53820396a980b5835426c33'
  headers = {"Authorization": TOKEN}

  def __init__(self, repo_owner, repo_name, branch=None, since=None, until=None):
    self.repo_owner = repo_owner
    self.repo_name = repo_name
    self.branch = branch or 'master'
    self.since = since or "2020-01-01T00:00:00"
    self.until = until or "2030-01-01T00:00:00"

    self.variables = {
      "owner": self.repo_owner,
      "name": self.repo_name,
      "branch": self.branch,
      "since": self.since,
      "until": self.until,
      "after": ""
    }

  def run_query(self, query):
    try:
      r = requests.post('https://api.github.com/graphql', json={'query': query, 'variables': self.variables}, headers=self.headers)
      if r.status_code == 200:
        return r.json()
      else:
        raise Exception("Query failed to run by returning code of {}. {}".format(r.status_code, query))
    except Exception as e:
      print(e)

  def get_top_contributors(self):
    hasNextPage = True
    usage_data = []
    after = ''
    while hasNextPage:
      query = '''
        query($owner:String!, $name:String!, $branch:String!, $since:GitTimestamp!, $until:GitTimestamp!) {
          repository(owner:$owner, name:$name) {
            object(expression: $branch) {
              ... on Commit {
                history(since: $since, until: $until, %(after)s) {
                  totalCount
                  nodes {
                    author {
                      name
                      user {
                        login
                      }
                    }
                  }
                  pageInfo {
                    startCursor
                    hasNextPage
                    hasPreviousPage
                    endCursor
                  }
                }
              }
            }
          }
        }''' % {"after": after}

      query_data = self.run_query(query)
      if not query_data:
        return usage_data
      data = query_data['data']['repository']['object']['history']
      usage_data += data['nodes']
      after = 'after:"{}"'.format(data['pageInfo']['endCursor'])
      hasNextPage = data['pageInfo']['hasNextPage']

      x = dict(collections.Counter([d.get('author',{'user': ''}).get('user',{'login':''}).get('login','') for d in usage_data if d.get('author',{'user': ''}).get('user')]))
      sorted_dict = collections.OrderedDict(sorted(x.items(), key=lambda kv: kv[1], reverse=True))
      usage_data = list(sorted_dict.items())[:30]

    return usage_data
  
  def get_prs(self):
    hasNextPage = True
    usage_data = []
    after = ''
    while hasNextPage:
      query = '''
        {
          search(first: 100, query: "repo:%(owner)s/%(name)s is:pr created:%(since)s..%(until)s", type: ISSUE, %(after)s) {
            nodes {
              ... on PullRequest {
                title
                state
                createdAt
                author {
                  login
                }
              }
            }
            pageInfo {
              endCursor
              hasNextPage
              hasPreviousPage
              startCursor
            }
          }
        }''' % {**self.variables, "after": after}

      query_data = self.run_query(query)
      if not query_data:
        return usage_data
      data = query_data['data']['search']
      usage_data += data['nodes']
      after = 'after:"{}"'.format(data['pageInfo']['endCursor'])
      hasNextPage = data['pageInfo']['hasNextPage']

    return usage_data
  
  def get_old_open_prs(self):
    usage_data = self.get_prs()
    days_considered_old = 30
    return [x for x in usage_data if x['state'] == 'OPEN' and (datetime.today() - datetime.strptime(x['createdAt'], "%Y-%m-%dT%H:%M:%SZ")).days > days_considered_old]
  
  def get_issues(self):
    hasNextPage = True
    usage_data = []
    after = ''
    while hasNextPage:
      query = '''
        {
          search(first: 100, query: "repo:%(owner)s/%(name)s is:issue created:%(since)s..%(until)s", type: ISSUE, %(after)s) {
            nodes {
              ... on Issue {
                title
                state
                createdAt
                author {login}
              }
            }
            pageInfo {
              endCursor
              hasNextPage
              hasPreviousPage
              startCursor
            }
          }
        }''' % {**self.variables, "after": after}

      query_data = self.run_query(query)
      if not query_data:
        return usage_data
      data = query_data['data']['search']
      usage_data += data['nodes']
      after = 'after:"{}"'.format(data['pageInfo']['endCursor'])
      hasNextPage = data['pageInfo']['hasNextPage']

    return usage_data
  
  def get_old_open_issues(self):
    usage_data = self.get_issues()
    days_considered_old = 14
    return [x for x in usage_data if x['state'] == 'OPEN' and (datetime.today() - datetime.strptime(x['createdAt'], "%Y-%m-%dT%H:%M:%SZ")).days > days_considered_old]
  
if __name__== "__main__":
  if len(sys.argv) == 1:
    print('Запускай с параметрами [repo_owner] [repo_name] [period_since] [period_until] [branch]')
  elif len(sys.argv) == 2:
    print('Не хватает обязательного параметра [repo_name]')
  
  params = dict()
  if len(sys.argv) >= 3:
    params = dict(repo_owner = sys.argv[1],repo_name = sys.argv[2])
  if len(sys.argv) >= 4:
    since = datetime.strptime(sys.argv[3], "%Y-%m-%d")
    params['since'] = since.strftime('%Y-%m-%dT%H:%M:%SZ')
  if len(sys.argv) >= 5:
    until = datetime.strptime(sys.argv[4], "%Y-%m-%d")
    params['until'] = until.strftime('%Y-%m-%dT%H:%M:%SZ')
  if len(sys.argv) >= 6:
    params['branch'] = sys.argv[5]

  if params:
    gq = graphQL(**params)
    
    print('Самые активные участники')
    pprint(gq.get_top_contributors())
    print('Количество открытых и закрытых pull requests')
    pprint(gq.get_prs())
    print('Количество “старых” pull requests')
    pprint(gq.get_old_open_prs())
    print('Количество открытых и закрытых issues')
    pprint(gq.get_issues())
    print('Количество “старых” issues')
    pprint(gq.get_old_open_issues())