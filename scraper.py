import re
import nltk
import time
nltk.download('punkt')
from urllib.parse import urlparse, urljoin, urldefrag
from urllib import robotparser
import urllib.request
from bs4 import BeautifulSoup
from collections import defaultdict
import ssl
ssl._create_default_https_context = ssl._create_unverified_context

VISITED = set()
VALID_URL_SET = {".ics.uci.edu/", ".cs.uci.edu/", ".informatics.uci.edu/", ".stat.uci.edu/", "today.uci.edu/department/information_computer_sciences/"}

#SIMHASH_DICT{url : 8-bit fing}
SIMHASH_LIST = []
INFINITE_URL_COUNT = defaultdict(int) # check if a certain domain/path has been visited 100+ times
LONGEST_PAGE_COUNT = -1
LONGEST_PAGE = ""
WORDS_COUNT = defaultdict(int)
THRESHOLD = 20 # infinite trap
BLACKLISTED = set()
URL_CONTENT_LENGTH = {}

SUBDOMAINS_COUNT = defaultdict(int)

STOPWORDS = nltk.corpus.stopwords.words('english')
STOPWORDS.append({"we've", 'cannot', "they're", "they've", "let's", "where's", "when's", 'could', "he's", "here's", "who's", "we'd", "he'll", "why's", 'ought', "she'd", "i'll", 'would', "i'm", "i've", "that's", "we'll", "can't", "they'll", "they'd", "he'd", "we're", "what's", "how's", "there's", "i'd", "she'll"})
# stopwords is NLTK's + the ones in the first list that the professor gave

# report details

def report():
    # if necessary: use global keyword for the global vars
    
    print('***************************** UNIQUE PAGES FOUND: ', len(VISITED))
    print("***************************** LONGEST PAGE: ", LONGEST_PAGE)
    print("***************************** LONGEST PAGE COUNT: ", LONGEST_PAGE_COUNT)
    for word, num_occ in sorted(WORDS_COUNT.items(), key=lambda item: item[1], reverse = True)[:50]:
        print("********* COMMON WORD: ",  word, "   NUM OF OCCURENCE: ", num_occ)
        
    print("*** NUMBER OF UNIQUE SUBDOMAINS FOUND ***: ", len(SUBDOMAINS_COUNT))

    for key in sorted(SUBDOMAINS_COUNT):
        value = SUBDOMAINS_COUNT[key]
        print("SUBDOMAIN:", key, ", ", value)

    with open('report.txt', 'w') as report_file:
        report_file.write('*** NUMBER OF UNIQUE PAGES FOUND ***\n')
        report_file.write(str(len(VISITED)))
        report_file.write('\n')
        
        report_file.write('*** LONGEST PAGE ***\n')
        report_file.write(LONGEST_PAGE)
        report_file.write('\n')

        report_file.write('*** LONGEST PAGE COUNT ***\n')
        report_file.write(str(LONGEST_PAGE_COUNT))
        report_file.write('\n')

        for word, num_occ in sorted(WORDS_COUNT.items(), key=lambda item: item[1], reverse = True)[:50]:
            report_file.write('*** COMMON WORD ***   \n')
            report_file.write(word)
            report_file.write('   *** COUNT ***   \n')
            report_file.write(str(num_occ))
            report_file.write('\n')

        report_file.write("*** NUMBER OF UNIQUE SUBDOMAINS FOUND ***\n")
        report_file.write(str(len(SUBDOMAINS_COUNT)))
        report_file.write('\n')

        for key in sorted(SUBDOMAINS_COUNT):
            value = str(SUBDOMAINS_COUNT[key])
            report_file.write('*** SUBDOMAIN ***\n')
            report_file.write(key)
            report_file.write('    ')
            report_file.write(value)
            report_file.write('\n')

        
# --------------- ORIGINAL: SCRAPER() ---------------
def scraper(url, resp):
    links = extract_next_links(url, resp)
    # count words and keep track of frequency of words
    with open('count.txt', "w") as f:
        print(WORDS_COUNT, file=f)
    return [link for link in links if is_valid(link)]

# --------------- FOR REPORT: SUBDOMAIN_CHECK() ---------------
def subdomain_check(url):
    if "ics.uci.edu" in url:
        scheme_subdomain = url.split("ics.uci.edu")[0]
        if scheme_subdomain and "www" not in scheme_subdomain:
            key = scheme_subdomain + "ics.uci.edu"
            SUBDOMAINS_COUNT[key] += 1

# --------------- SIMHASH (CHECK FOR SIMILAR PAGES) ---------------
def sim_hash(freq_dict):
    v = [0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0]      
    for key, count in freq_dict.items():
        hashkey = hash(key) % 65535
        binary = format(hashkey, "016b")
        for i, bit in enumerate(binary):
            if bit == '0':
                v[i] -= count
            else:
                v[i] += count
    for i, num in enumerate(v):
        if num > 0:
            v[i] ='1'
        else:
            v[i] ='0'
    return ''.join(v)

def compare_sim_hashes(sh_A, sh_B):
    # return similarity: the fraction of the bits that are the same over 
    # all n bits of the representation.
    num_bits_same = 0
    for i in range(len(sh_A)):
        if sh_A[i] == sh_B[i]:
            num_bits_same += 1
    return num_bits_same / 16

def is_near_duplicate(similarity):
    # threshold is 0.8
    return similarity >= 0.8

# --------------------------------------------------------------------

def extract_next_links(url, resp):

    global VISITED
    global LONGEST_PAGE
    global LONGEST_PAGE_COUNT
    global THRESHOLD
    global INFINITE_URL_COUNT
    global WORDS_COUNT
    global BLACKLISTED
    global URL_CONTENT_LENGTH
    
    VISITED.add(url)
    
    # --------------- URL WITHOUT QUERY (FOR INFINITE TRAPS) ---------------
    # this url (with query removed) is used to check for infinite traps
    # url_without_query = urlparse(url).scheme + '://' + urlparse(url).netloc # DEBUG 
    url_without_query = urlparse(url).scheme + '://' + urlparse(url).netloc + urlparse(url).path
    
    new_urls = []
    
    if resp.status == 200 and (url_without_query not in BLACKLISTED):
        
        # --------------- RESPECT ROBOT.TXT ---------------

        # use robot.txt to see if we are allowed to crawl
        # slice url to get the root page, and append '/robots.txt'
        # ex: 'https://google.com/foo/bar' -> 'https://google.com/robots.txt

        rp = robotparser.RobotFileParser()
        
        robot_page = urlparse(url).scheme + '://' + urlparse(url).netloc + '/robots.txt'

        rp.set_url(robot_page)

        rp.read()
        
        # ---------------------------------------------
        
        if rp.can_fetch("*", url):

            if resp.raw_response.content:   # checks if url has data
                with open('output.txt', "w") as file:
                    
                    file.write('LENGTH VISITED SO FAR: \n')
                    file.write(str(len(VISITED)))
                    file.write('\n')

                    # check if this url (defragged) is a subdomain
                    subdomain_check(urldefrag(url))
                    
                    # ----------------  BEAUTIFULSOUP + TOKENIZER ----------------

                    soup = BeautifulSoup(resp.raw_response.content, 'html.parser')
                    # tokenize text here
                    text = soup.get_text()
                    tokens = nltk.word_tokenize(text)


                    # ----------------  SIM HASHES (CHECK FOR SIMILAR PAGES) ----------------
                    
                    # check if similar
                    url_freq_dict = defaultdict(int)

                    for word in tokens:
                        word_lower = word.lower()
                        if word_lower not in STOPWORDS and word.isalpha(): # justification: only interested
                            url_freq_dict[word_lower] += 1
                    
                    url_binary = sim_hash(url_freq_dict)
                    
                    similar = False
                    
                    for b in SIMHASH_LIST:
                        if is_near_duplicate(compare_sim_hashes(b, url_binary)):
                            similar = True

                    if not similar:
                        SIMHASH_LIST.append(url_binary)
                        # process tokenize using nltk, add to defaultdict
                        if len(tokens) > LONGEST_PAGE_COUNT:
                            LONGEST_PAGE_COUNT = len(tokens)
                            LONGEST_PAGE = url
                        for word, count in url_freq_dict.items():
                            WORDS_COUNT[word] += count

        
                            # ----------------  DISCOVER NEW URLS VIA BEAUTIFULSOUP ----------------
                        response = urllib.request.urlopen(url)
                        if response.getcode() == 200:

                            # --------- URL CONTENT LENGTH ---------
                            # add url and content length to.txt URL_CONTENT_LENGTH
                            # and write to urlcontentlength        
                            URL_CONTENT_LENGTH[url] = response.getheader('Content-Length')
                            print('========URL CONTENT LENGTH========', URL_CONTENT_LENGTH[url]) 
                            with open('urlcontentlength.txt', 'a') as file:
                                file.write('========URL CONTENT LENGTH========')
                                file.write(url)
                                file.write(': ')
                                if URL_CONTENT_LENGTH[url] != None:
                                    file.write(URL_CONTENT_LENGTH[url])
                                file.write('\n')

                            # --------- GET ALL LINKS ---------
                            for link in soup.find_all('a'):
                                final = urldefrag(urljoin(url, link.get('href')).rstrip('/'))[0]
                            
                                if (final not in VISITED) and (final not in new_urls) and (url_without_query not in BLACKLISTED):
                                    for valid_url_domains in VALID_URL_SET:
                                        # check if url is any of the domains specified in the assignment
                                        # check if frequency of this url has exceeded threshold
                                        # check if url is not in blacklisted (aka not an infinite trap)
                                        # TODO: check if url is not a pdf 
                                        if valid_url_domains in final:

                                            # add url to dictionary and increase frequency of url
                                            INFINITE_URL_COUNT[url_without_query] += 1

                                            # ----------- CHECK IF SHOULD THIS IS AN INFINITE TRAP ----------------
                                            if INFINITE_URL_COUNT[url_without_query] < THRESHOLD:

                                                # add url to list of new urls
                                                new_urls.append(final)

                                            # otherwise, add url to blacklisted so we don't visit this future infinite url trap again
                                            else:
                                                BLACKLISTED.add(url_without_query)
                                                print('BLACKLISTED URL: ', url_without_query)
                        
                        # --------------------------------------------------------------------------------


                        # ----------------------NLTK TOKENIZE --------------------------
                        # process tokenize using nltk, add to defaultdict
                        if len(tokens) > LONGEST_PAGE_COUNT:
                            LONGEST_PAGE_COUNT = len(tokens)
                            LONGEST_PAGE = url
                        for word in tokens:
                            word_lower = word.lower()
                            if word_lower not in STOPWORDS and word.isalpha(): # justification: only interested
                                WORDS_COUNT[word_lower] += 1
                                

    # elif resp.status == 300: # multiple choice redirect
    #     pass
    elif resp.status == 301: # moved permanently
        print('error 301')
        opener = urllib.request.build_opener()
        request = urllib.request.Request(url)
        opened = opener.open(request)
        print(opened.geturl())

    elif resp.status == 302: #Found
        pass
    elif resp.status == 303: #See other
        pass
    elif resp.status == 307: # temporary redirect
        pass 
    elif resp.status == 308: # permanent redirect
        pass

    else:
        if (resp.status != 200):
            print("An error occurred: ", resp.status)
        else:
            print("Site has been blacklisted")
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