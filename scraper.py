import re
import nltk
import time
nltk.download('punkt')
from urllib.parse import urlparse, urljoin, urldefrag
from urllib import robotparser
from bs4 import BeautifulSoup
from collections import defaultdict

VISITED = set()
LONGEST_PAGE_COUNT = -1
LONGEST_PAGE = ""
WORDS_COUNT = defaultdict(int)

STOPWORDS = nltk.corpus.stopwords.words('english')
STOPWORDS.append({"we've", 'cannot', "they're", "they've", "let's", "where's", "when's", 'could', "he's", "here's", "who's", "we'd", "he'll", "why's", 'ought', "she'd", "i'll", 'would', "i'm", "i've", "that's", "we'll", "can't", "they'll", "they'd", "he'd", "we're", "what's", "how's", "there's", "i'd", "she'll"})
# stopwords is NLTK's + the ones in the first list that the professor gave


def scraper(url, resp):
    links = extract_next_links(url, resp)
    # count words and keep track of frequency of words
    with open('count.txt', "w") as f:
        print(WORDS_COUNT, file=f)
    return [link for link in links if is_valid(link)]

def extract_next_links(url, resp):
    # Implementation required.
    # url: the URL that was used to get the page
    # resp.url: the actual url of the page
    # resp.status: the status code returned by the server. 200 is OK, you got the page. Other numbers mean that there was some kind of problem.
    # resp.error: when status is not 200, you can check the error here, if needed.
    # resp.raw_response: this is where the page actually is. More specifically, the raw_response has two parts:
    #         resp.raw_response.url: the url, again
    #         resp.raw_response.content: the content of the page!
    # Return a list with the hyperlinks (as strings) scrapped from resp.raw_response.content

    VISITED.add(url)
    # print('VISITED: ', VISITED)
    new_urls = []
    if resp.status == 200:
        # use robot.txt to see if we are allowed to crawl
        rp = robotparser.RobotFileParser()
        # slice url to get the root page, and append '/robots.txt'
        # ex: 'https://google.com/foo/bar' -> 'https://google.com/robot.txt
        root_page = urlparse(url).scheme + '://' + urlparse(url).netloc + '/robots.txt'
        rp.set_url(root_page)
        rp.read()
        if rp.can_fetch("*", url):
            # politeness
            time.sleep(rp.crawl_delay("*"))
            if resp.raw_response.content:
                with open('output.txt', "w") as file:
                    soup = BeautifulSoup(resp.raw_response.content, 'html.parser')
                    # tokenize text here
                    text = soup.get_text()
                    tokens = nltk.word_tokenize(text)
                    # print(soup.prettify())
                    for link in soup.find_all('a'):
                        final = urldefrag(urljoin(url, link.get('href')).rstrip('/'))[0]

                        file.write(final)
                        file.write('\n')

                        if final not in VISITED and final not in new_urls:
                            new_urls.append(final)
                            # process tokenize using nltk, add to defaultdict
                    if len(tokens) > LONGEST_PAGE_COUNT:
                        LONGEST_PAGE_COUNT = len(tokens)
                        LONGEST_PAGE = url
                    for word in tokens:
                        word_lower = word.lower()
                        if word_lower not in STOPWORDS:
                            WORDS_COUNT[word_lower] += 1

                #print('[SCRAPER] new_urls: ', new_urls)

                # check hyperlinks and scrape them
    else:
        print("An error occurred: ", resp.status)
    return new_urls

def is_valid(url):
    # Decide whether to crawl this url or not. 
    # If you decide to crawl it, return True; otherwise return False.
    # There are already some conditions that return False.
    try:
        parsed = urlparse(url)
        if parsed.scheme not in set(["http", "https"]):
            return False
        return not re.match(
            r".*\.(css|js|bmp|gif|jpe?g|ico"
            + r"|png|tiff?|mid|mp2|mp3|mp4"
            + r"|wav|avi|mov|mpeg|ram|m4v|mkv|ogg|ogv|pdf"
            + r"|ps|eps|tex|ppt|pptx|doc|docx|xls|xlsx|names"
            + r"|data|dat|exe|bz2|tar|msi|bin|7z|psd|dmg|iso"
            + r"|epub|dll|cnf|tgz|sha1"
            + r"|thmx|mso|arff|rtf|jar|csv"
            + r"|rm|smil|wmv|swf|wma|zip|rar|gz)$", parsed.path.lower())

    except TypeError:
        print ("TypeError for ", parsed)
        raise
