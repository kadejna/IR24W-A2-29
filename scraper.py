import re
from urllib.parse import urlparse, urljoin
from bs4 import BeautifulSoup

visited = {} # keep track of visited pages for similarity detection 
# keep track of unqiue pages - Uniqueness for the purposes of this assignment is ONLY established by the URL, but discarding the fragment part. So, for example, http://www.ics.uci.edu#aaa and http://www.ics.uci.edu#bbb are the same URL
unique_pages = set()
# keep track of the longest page in terms of the number of words (HTML markup doesn't count as words)
longest_page = {"url": "", "word_count": 0}
# keep track of the 50 most common words ordered by its frequency - ignore english stop words
common_words = {}
# stop words to ignore 
stop_words = [
    "a", "about", "above", "after", "again", "against", "all", "am", "an", "and",
    "any", "are", "aren't", "as", "at", "be", "because", "been", "before", "being",
    "below", "between", "both", "but", "by", "can't", "cannot", "could", "couldn't",
    "did", "didn't", "do", "does", "doesn't", "doing", "don't", "down", "during",
    "each", "few", "for", "from", "further", "had", "hadn't", "has", "hasn't", "have",
    "haven't", "having", "he", "he'd", "he'll", "he's", "her", "here", "here's", "hers",
    "herself", "him", "himself", "his", "how", "how's", "i", "i'd", "i'll", "i'm", "i've",
    "if", "in", "into", "is", "isn't", "it", "it's", "its", "itself", "let's", "me", "more",
    "most", "mustn't", "my", "myself", "no", "nor", "not", "of", "off", "on", "once", "only",
    "or", "other", "ought", "our", "ours", "ourselves", "out", "over", "own", "same", "shan't",
    "she", "she'd", "she'll", "she's", "should", "shouldn't", "so", "some", "such", "than", "that",
    "that's", "the", "their", "theirs", "them", "themselves", "then", "there", "there's", "these", "they",
    "they'd", "they'll", "they're", "they've", "this", "those", "through", "to", "too", "under", "until", "up",
    "very", "was", "wasn't", "we", "we'd", "we'll", "we're", "we've", "were", "weren't", "what", "what's", "when",
    "when's", "where", "where's", "which", "while", "who", "who's", "whom", "why", "why's", "with", "won't", "would",
    "wouldn't", "you", "you'd", "you'll", "you're", "you've", "your", "yours", "yourself", "yourselves"
]
# keep track of the subdomains you find in the ics.uci.edu domain - list of subdomains ordered alphabetically and the number of uniques pages detected in each subdomain. the content of this list should be lines containing URL, number for example: http://vision.ics.uci.edu, 10
subdomains = {}
sorted_subdomains = {}

# scheme + path count 
relative_count = {}

# receives a URL and corresponding web response for example, "http://www.ics.uci.edu" and the web response will contain the page itself 
def scraper(url, resp):
    links = extract_next_links(url, resp)
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

    global unique_pages, longest_page, common_words, stop_words, subdomains, sorted_subdomains, relative_count 
    # store hyperlinks scrapped from resp.raw_response.content
    links = []

    try: 
        # if the status code is 200 and the url is valid 
        if resp.status == 200 and is_valid(url):
            # Detect and avoid dead URLs that return a 200 status but no data (204 No Content)
            if resp.status == 204 or resp.raw_response.content == "":
                print("The page is empty.")
                return links

            # Detect and avoid crawling very large files, especially if they have low information value

            # parse the content of the page
            print("Parsing the content of the page...")
            content = resp.raw_response.content
            soup = BeautifulSoup(content, "html.parser")
            # filter out tags for "Good Content" of the page - removes hyperlinks, navbars, footers, etc.
            # filter out tags for "Good Content" of the page - removes hyperlinks, navbars, footers, etc.
            filtered_tags = soup.find_all(lambda tag: tag.name in ['title', 'p', 'h1', 'h2', 'h3', 'ul', 'ol', 'li', 'table', 'tr', 'td'] and not any(parent.name in ['nav', 'header', 'footer'] for parent in tag.parents))

            # get the text from filtered_tags
            text = " ".join([tag.get_text() for tag in filtered_tags])

            # tokenize the text and put the url and the tokens in a text file 
            tokens = tokenize(text)
            # store the tokens in a text file
            with open("tokens.txt", "a") as file:
                file.write("URL: " + url + "\n")
                file.write("Tokens: ")
                for token in tokens:
                    file.write(token + ", ")
                file.write("\n")

            # # if it doesn't meet a certain amount of words, consider it as low info content 
            # if len(tokens) < 30:
            #     print("The page has less than 30 words.")
            #     return links

            # # when we check for similarity, do we wanna check every single link that we have visited? 
            # # Check similarity with already visited pages to avoid crawling the similar page multiple times
            # for visited_url, visited_text in visited.items():
            #     # Compares the current page with the visited pages and if it is similar, it returns an empty list
            #     # only compare if the pages are similar if they are in the same domain in terms of relative path 
            #     # DO WE CHECK THE "LINK" or the "URL"? 
            #     # put the print result in a text file 
            #     with open("similarity.txt", "a") as file:
            #         file.write("Comparing " + url + " and " + visited_url + "...\n")
            #     if url.rsplit('/', 1)[0] + "/" == visited_url.rsplit('/', 1)[0] + "/" and is_similar_fingerprint(text, visited_text):
            #         print("The page is similar to a page already visited.")
            #         # DO WE EXIT THE FUNCTION AND GO TO THE NEXT URL IF THE PAGE IS SIMILAR TO A PAGE ALREADY VISITED?
            #         return links

            # count occurrences of words in the content
            words = [word.lower() for word in tokenize(text) if word.lower() not in stop_words]
            # update common_words dictionary
            for word in words:
                common_words[word] = common_words.get(word, 0) + 1

            # extract subdomain from the URL
            subdomain = urlparse(url).hostname
            # update subdomains dictionary
            if subdomain.endswith(".ics.uci.edu"):
                subdomains[subdomain] = subdomains.get(subdomain, 0) + 1
            # get subdomains ordered alphabetically
            sorted_subdomains = sorted(subdomains.items(), key=lambda x: x[0])

            current_page_length = len(tokenize(text))
            # compare the current page length with whats in the longest_page's word_count
            if current_page_length > longest_page['word_count']:
                longest_page['url'] = url
                longest_page['word_count'] = current_page_length

            # count the relative path of the URL for trap detection 
            # IF THE LENGTH OF THE SPLIT IS LESS THAN 2, WE THEN DOWNLOAD IT.........
            relative = url.rsplit('/', 1)[0] + "/"
            relative_count[relative] = relative_count.get(relative, 0) + 1
            if relative_count[relative] > 15: 
                return links 

            # print the link and the relative path count in a text file 
            with open("relative_count.txt", "a") as file:
                file.write("Relative URL: " + relative + "\n")
                file.write("Relative Path Count: " + str(relative_count[relative]) + "\n")

            # crawling/scrapping - find all the hyperlinks in the page
            for tag in soup.find_all('a', href=True):
                # make sure crawler doesn't fall into a trap of infinite loops
                link = tag.get('href')

                if is_valid(link):
            
                    # transform relative URLs to absolute URLs - if the link is a relative URL, append it to the base URL
                    if link.startswith("/"):
                        link = urljoin(url, link)
                    elif link.startswith(("http", "https")):
                        link = link
                    else:
                        link = urljoin(url, "/" + link)

                    # defragment the URL only if the fragment exists and add it to the unique URLs list
                    if "#" in link:
                        link = link.split("#")[0]
                        # # check if the path count exceeds a threshold
                        # if relative_count[relative] <= 5:
                        unique_pages.add(link)
                        links.append(link)
                        visited[link] = text

                    # if the page doesn't have a fragment, you still add it to the unique URLs list
                    else:
                        # # check if the path count exceeds a threshold
                        # if relative_count[relative] <= 5:
                        unique_pages.add(link)
                        links.append(link)
                        visited[link] = text
        
        # detect redirects and if the page redirects your crawler, index the redirected content
        # go into the content of the redirected page
        # anything that starts with 3 is a redirect
        elif resp.status == 301 or resp.status == 302:
            print("The page is a redirect.")
            # if the page is a redirect, index the redirected content
            redirected_url = resp.raw_response.url
            redirected_content = resp.raw_response.content
            soup = BeautifulSoup(redirected_content, "html.parser")

        # write unique_pages and the total number of unique pages to a txt file
        with open("unique_pages.txt", "w") as file:
            for page in unique_pages:
                file.write(page + "\n")
            file.write("Total Unique Pages: " + str(len(unique_pages)))

        # write longest page's url and word_count to a txt file
        with open("longest_page.txt", "w") as file:
            file.write("Longest Page: " + longest_page['url'] + "\n")
            file.write("Word Count: " + str(longest_page['word_count']))

        # write common_words to a txt file
        with open("common_words.txt", "w") as file:
            for word, count in common_words.items():
                file.write(word + ": " + str(count) + "\n")
        # write most common words to a text file 
        with open("most_common_words.txt", "w") as file:
            for word, count in sorted(common_words.items(), key=lambda x: x[1], reverse=True)[:50]:
                file.write(word + ": " + str(count) + "\n")

        # write subdomains to a txt file
        with open("subdomains.txt", "w") as file:
            for subdomain, count in sorted_subdomains:
                file.write(subdomain + ": " + str(count) + "\n")

    except Exception as e: 
        print("An error occurred while links were extracted: ", e)

    # return the list of scrapped hyperlinks 
    return links

def is_valid(url):
    # Decide whether to crawl this url or not. 
    # If you decide to crawl it, return True; otherwise return False.
    # There are already some conditions that return False.
    try:
        parsed = urlparse(url)
        if parsed.scheme not in set(["http", "https"]):
            return False

        # make sure to return only URLs that are within the domains and paths specified
        netloc = parsed.netloc
        allowed_domains = [".ics.uci.edu", ".cs.uci.edu", ".informatics.uci.edu", ".stat.uci.edu"]
        # allowed_domains = [".stat.uci.edu"]
        if not any(domain in netloc for domain in allowed_domains):
            return False

        # if a URL's query contains action=download or ical, return False 
        if "action=download" in parsed.query:
            return False

        if "ical=1" in parsed.query:
            return False 
            
        # if a URL's path contains '/wp-content/uploads', return False 
        if "/wp-content/uploads" in parsed.path:
            return False

        if "pdf" in parsed.path: 
            return False 

        # modified to ensure we are only crawling URLs that are web pages and not files
        return not re.match(
            r".*\.(css|js|bmp|gif|jpe?g|ico"
            + r"|png|tiff?|mid|mp2|mp3|mp4"
            + r"|wav|avi|mov|mpeg|ram|m4v|mkv|ogg|ogv|pdf"
            + r"|ps|eps|tex|ppt|pptx|doc|docx|xls|xlsx|names"
            + r"|data|dat|exe|bz2|tar|msi|bin|7z|psd|dmg|iso"
            + r"|epub|dll|cnf|tgz|sha1"
            + r"|thmx|mso|arff|rtf|jar|csv"
            + r"|txt|ppsx|war|r|bib|mat|m|uai|java|py|scm|rkt|ss|sql|odc|img"
            + r"|rm|smil|wmv|swf|wma|zip|rar|gz)$", parsed.path.lower())

    except TypeError:
        print ("TypeError for ", parsed)
        raise

# tokenizes the text 
def tokenize(text):
    # lowercase all words to be independent of capitalization
    text = text.lower()
    # use regex to find all the words that are a "token"
    # exclude periods at the end of sentences but include them in abbreviations
    tokens = re.findall(r"(?:\w+\.\w+|\w+['’]\w+|\w+)", text)
    # return the list of "tokens" that are found from the text
    return tokens

# implement a fingerprint function for similarity between two pages
# document is first parsed into words
# the words are grouped into contiguous n-grams for some n like 3-grams
# some of the n-grams are selected to represent the document
# the selected n-grams are hashed to improve literal efficiency
# the hash values are stored, and documents are compared using the overlap of fingerprints
def is_similar_fingerprint(page1_text, page2_text, n=3, threshold=15):
    # tokenize the text
    page1_tokens = tokenize(page1_text)
    page2_tokens = tokenize(page2_text)

    # create a set of n-grams for each page
    page1_ngrams = set()
    page2_ngrams = set()
    for i in range(len(page1_tokens) - n + 1):
        ngram = tuple(page1_tokens[i:i+n])
        page1_ngrams.add(ngram)
    for i in range(len(page2_tokens) - n + 1):
        ngram = tuple(page2_tokens[i:i+n])
        page2_ngrams.add(ngram)

    # hash n-grams
    hashed_page1_ngrams = set(hash(ngram) for ngram in page1_ngrams)
    hashed_page2_ngrams = set(hash(ngram) for ngram in page2_ngrams)

    # select hashes using H mod 4 = 0
    selected_hashes_page1 = set(hash_value for hash_value in hashed_page1_ngrams if hash_value % 4 == 0)
    selected_hashes_page2 = set(hash_value for hash_value in hashed_page2_ngrams if hash_value % 4 == 0)

    # if the pages have no selected hashes in common, they are not similar
    if len(selected_hashes_page1.union(selected_hashes_page2)) == 0: 
        return False 

    # compare documents using the overlap of fingerprints
    common_hashes = selected_hashes_page1.intersection(selected_hashes_page2)
    similarity = len(common_hashes) / len(selected_hashes_page1.union(selected_hashes_page2)) * 100

    # write it into similarity.txt here too 
    with open("similarity.txt", "a") as file:
        file.write(f"Similarity: {similarity}%\n")

    # return true if the similarity is greater than the threshold
    return similarity >= threshold

# # checks if two pages are similar
# def is_similar(page1_text, page2_text): 
#     page1_tokens = set(tokenize(page1_text))
#     page2_tokens = set(tokenize(page2_text))

#     common_tokens = page1_tokens.intersection(page2_tokens)
#     union_tokens = page1_tokens.union(page2_tokens)
#     similarity = (len(common_tokens) / len(union_tokens)) * 100
    
#     print(f"Similarity: {similarity}%")
    
#     return similarity <= 90
 
# main function to test 
if __name__ == "__main__":
    # url = "https://wics.ics.uci.edu/events/2022-05-22"
    # url = "https://wics.ics.uci.edu/events/2022-05-23/?ical=1"
    url = "https://wics.ics.uci.edu/category/news/page/26"
    
    parsed = urlparse(url)
    print(parsed)
    relative = url.rsplit('/', 1)[0] + "/"
    # up until the last part of the path
    # relative = parsed.scheme + "://" + parsed.netloc + parsed.path[]
    print(relative)
#     url = "http://www.stat.uci.edu/wp-content/uploads/JuliaPalaciosAbstract6-6-19"
#     print(urlparse(url))
    # page1 = "https://www.stat.uci.edu/professors-nan-and-gillen-receive-1-8m-grant-to-study-statistical-methods-for-alzheimers-research"
    # page2 = "https://www.stat.uci.edu/uci-in-top-10-on-fortunes-list-of-best-masters-in-data-science-programs"

    # print(page1.rsplit('/', 1)[0] + "/")
    # print(page2.rsplit('/', 1)[0] + "/")

    # url = "http://sli.ics.uci.edu/Classes/2016S-274b?action=download&upname=HW4c.zip"
    # print(urlparse(url))
    # if "action=download" in urlparse(url).query:
    #     print("DOWNLOAD")

    # wics_url = "https://wics.ics.uci.edu/events/2022-02-20"
    # # get https://wics.ics.uci.edu/events/ from the url 
    # print(urlparse(wics_url).path)
    # print(wics_url.rsplit('/', 1)[0] + "/")
    # google_url = "https://www.google.com/calendar/event?action=TEMPLATE&text=Fall+2022+Week+4%3A+Committee+Applications+Panel&dates=20221019T180000/20221019T190000&details=RSVP%3A+https%3A%2F%2Fbit.ly%2FWICSxCommitteeAppsPanel%C2%A0+%0AWanna+join+our+team%3F+WICS+Committee+applications+are+now+open%2C+and+we%E2%80%99re+here+to+answer+any+questions+you+may+have%2C+from+how+often+we+meet+to+what+we+love+about+being+on+committee.+Join+us+as+our+panelists+from+each+committee+share+with+you+their+experiences+and+all+of+the+reasons+why+you+should+apply%21+Snacks+will+be+provided%2C+so+be+sure+to+RSVP.+Note+that+everyone+is+welcome%2C+regardless+of+gender+identity.+See+you+there%21+%0A%0A%0A%09Related%0A&location=ICS+428&trp=false&sprop=website:https://wics.ics.uci.edu&ctz=America%2FLos_Angeles"
    # # https://wics.ics.uci.edu/events/ 15
    # path = urlparse(google_url).path
    # print(path)
    # print(urlparse(google_url).netloc)
    # print(path.split('/')[-1])

    # # given "https://wics.ics.uci.edu/events/2022-02-20", get "https://wics.ics.uci.edu/events/"
    # # print(url.rsplit('/', 1)[0] + "/")

    # url1 = "https://wics.ics.uci.edu/events/2021-10-11/"
    # url2 = "https://wics.ics.uci.edu/events/2021-10-10/"
    # # how do you test if the resp content that is associated with the url is not here? 
    # # print(is_similar(get_page(url1), get_page(url2)))

