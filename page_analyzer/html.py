from bs4 import BeautifulSoup


def get_seo(html):
    soup = BeautifulSoup(html, 'html.parser')
    title = soup.title.string if soup.title else ''
    h1 = soup.h1.string if soup.h1 else ''
    meta = soup.find('meta', attrs={'name': 'description'})
    description = meta.get('content') if meta else ''
    return title, h1, description
