from json import loads
from urllib import request, parse

from env import DP_URL

def write_dp(sub_page, content):
	full_url = ''.join([DP_URL, sub_page])
	data = parse.urlencode({'text' : content}).encode('utf-8')

	req = request.Request(full_url, data)

	with request.urlopen(req) as response:
		return response.read()

def read_dp(sub_page):
	full_url = [DP_URL, sub_page, '.body.json?lastUpdate=0']
	with request.urlopen(''.join(full_url)) as response:
		resp = response.read()

	return loads(resp.decode())['body']