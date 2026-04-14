from bs4 import BeautifulSoup

def html_to_text(html):
    soup = BeautifulSoup(html, "html.parser")
    return soup.get_text(separator=" ", strip=True)

# Example
html = "<html><body><h1>Hello</h1><p>World!</p></body></html>"
text = html_to_text(html)

print(text)