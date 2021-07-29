import requests
from bs4 import BeautifulSoup


url = 'https://www.wanted.co.kr/profile/interests'

response = requests.get(url)

# print(response.text)

soup = BeautifulSoup(response.text, 'html.parser')

for i in soup.findAll('meta'):
    # if 'property' in i.attrs:
    #     for j in i.attrs:
    #         if j == 'property':
                print(i.attrs)
