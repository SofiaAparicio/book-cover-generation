import json
import pathlib
import re
import os
from os import walk
from multiprocessing import Pool
from time import sleep
from typing import Any, Dict, List, Optional, Set, Union
from pathlib import Path

import requests
import urllib.request
from bs4 import BeautifulSoup
from tqdm import tqdm
from concurrent.futures import ThreadPoolExecutor

ROOT_URL = 'http://www.goodreads.com/'
MIN_NUM_BOOKS = 5000000
MIN_NUMB_RATINGS = 10000
MAX_NUM_BOOKS = 10000


def get_image(url: str) -> None:
    file_name = url.split("/")[-1]
    urllib.request.urlretrieve(url, f"././{file_name}")
    return True


def save_books(books: List[Dict[str, Any]], genre: str, save_dir: Optional[str] = None):
    save_dir = Path(save_dir or './data')
    if not save_dir.exists(): save_dir.mkdir()
    with open(save_dir / f'books_{genre}.json', 'w') as fp:
        json.dump(books, fp)


def get_book_info(url: str) -> Dict[str, Any]:
    """Extract information from Book.

    Args:
        url (str): Url of book.

    Returns:
        Dict[str, Any]: Extracted information.
    """   
    sleep(5)
    response = requests.get(url)
    soup = BeautifulSoup(response.content, 'html.parser')

    title, author = None, None
    title_author = soup.find('title')
    if title_author:
        title_author = title_author.string.split(' by ')
        title = title_author[0].strip()
        if len(title_author) > 1: author = title_author[1].strip()

    image_url = soup.find('meta', property='og:image')
    if image_url is not None: image_url = image_url['content']

    isbn13 = soup.find('meta', property='books:isbn')
    if isbn13 is not None: isbn13 = isbn13['content']

    num_pages = soup.find('meta', property='books:page_count')
    if num_pages is not None: num_pages = num_pages['content']

    avg_rating = soup.find('span', {'itemprop': 'ratingValue'})
    if avg_rating is not None: avg_rating = avg_rating.string.split('\n')[1].strip()

    num_ratings = soup.find('meta', {'itemprop': 'ratingCount'})
    if num_ratings is not None: num_ratings = num_ratings.string.split('\n')[1].strip()

    num_reviews = soup.find('meta', {'itemprop': 'reviewCount'})
    if num_reviews is not None: num_reviews = num_reviews.string.split('\n')[1].strip()

    
    language = soup.find('div', {'itemprop': 'inLanguage'})
    if language is not None: language = language.string
    
    genres = [genre.string for genre in soup.find('body').find_all('a', {'class': 'actionLinkLite bookPageGenreLink'})]

    return {
        'title': title,
        'author': author,
        'image_url': image_url,
        'isbn13': isbn13,
        'num_pages': num_pages,
        'avg_rating': avg_rating,
        'num_ratings': num_ratings,
        'num_reviews': num_reviews,
        'language': language,
        'genres': genres
    }


def get_genres() -> List[Dict[str, Union[str, int]]]:
    """Get all book genres.

    Returns:
        List[Dict[str, Union[str, int]]]: List of book genres and number of books.
    """    
    URL = "genres/list?page={page}"
    number_regex = re.compile(r'\d+[,\d{3}]*')
    genre_list = []

    next_url = "1" 
    while "next" not in  next_url:
        url = ROOT_URL + URL.format(page=next_url)
        html = requests.get(url).content
        data = BeautifulSoup(html, 'html.parser')
        parent = data.find("body").find_all("div", {"class": "shelfStat"})
        for child in parent:
            genre = child.find("a", {"class": "mediumText actionLinkLite"}).string
            nbooks = child.find("div", {"class": "smallText greyText"}).string
            nbooks = int(number_regex.search(nbooks).group().replace(',', ''))

            genre_list.append({
                'genre': genre,
                'num_books': nbooks
            })

        next_url = data.find("em", {"class": "current"}).findNext().string

    return genre_list


def get_books_links(genre: str, visited_links: Set[str]=set(), max_books: Optional[int]=None) -> List[str]:
    """Get books links for a given genre.

    Args:
        genre (str): Book genre.
        visited_links (Set[str]): Set with the visited links.
        max_books (Optional[int], optional): Maximum number of books. Defaults to None.

    Returns:
        List[str]: List of book URLs.
    """    
    URL = "shelf/show/{genre}?page={page}"
    page = 1 
    books = []

    url = ROOT_URL + URL.format(genre=genre, page=page)
    html = requests.get(url).content
    data = BeautifulSoup(html, 'html.parser')

    number_books = data.select_one('div[class=leftContainer] > div[class=mediumText] > span[class=smallText]').string
    max_number_books = int(re.search(r'Showing \d{1,3}-\d{1,3} of (\d+(,\d+)?)', number_books).group(1).replace(',',''))
    max_books = max_books or MAX_NUM_BOOKS

    pbar = tqdm(total=max_number_books, desc=f"Scrapping {genre} books links", leave=False)

    while max_number_books > 0 and  len(books) < max_books:
        all_books = data.select('div[class=leftContainer] > div[class=elementList]')
        for book in all_books:
            try:
                numb_ratings = int(book.find("span", {"class":"smallText"}).string.split("ratings")[0].split()[-1].replace(",", ""))
            except ValueError:
                continue
            if numb_ratings > MIN_NUMB_RATINGS:
                url_extension = book.find("a", {"class":"bookTitle"})['href']
                book_url = ROOT_URL + re.sub(r'^/', '', url_extension)
                if book_url not in visited_links: 
                    books.append(book_url)

            max_number_books -= 1
            pbar.update(1)
            if len(books) > max_books:
                break
        
        page += 1
        url = ROOT_URL + URL.format(genre=genre, page=page)
        sleep(1)
        html = requests.get(url).content
        data = BeautifulSoup(html, 'html.parser')

    return books


def scrapp_books_multiprocess(genre: str, visited_links: Set[str]=set(), num_threads: int = 10) -> List[Dict[str, Any]]:
    """Scraps all the books from one genre using multiprocessing.

    Args:
        genre (str): Book genre to be scrapped.
        visited_links (Set[str]): Set with the visited links.
        num_threads (int, optional): Numeber of threads to be used. Defaults to 10.

    Returns:
        List[Dict[str, Any]]: Book information.
    """    
    book_links = get_books_links(genre)
    visited_links |= set(book_links)
    with ThreadPoolExecutor(max_workers=num_threads) as executor:
        books_info = list(tqdm(executor.map(get_book_info, book_links), total=len(book_links), desc= f'Scrapping {genre} books', leave=False))

    return books_info, visited_links


def main():

    # visited_links, all_links = set(), []

    # # Get all the genders from Goodreads
    # all_genders = get_genres()

    # # Select only the genders with a number of books superior than MIN_NUM_BOOKS
    # selected_genres = [genre for genre in all_genders if genre["num_books"] > MIN_NUM_BOOKS]
    

    # Get the current working directory
    directory = os.getcwd()
    index = directory.find("book-cover-generation") + len("book-cover-generation") +1

    # Extract all files under the data directory
    data_path = directory[:index]+"/data/"
    filenames = next(walk(data_path), (None, None, []))[2] 

    # # Get list of names of categories already visited
    # all_visited_categories = {filename.split(".")[0].split("_")[-1]:filename for filename in filenames}
    
    # # Get the URL of every book of each genre
    # for genre in tqdm(selected_genres):
    #     if genre["genre"] in list(all_visited_categories.keys()):
    #         continue
    #     book_links = get_books_links(genre["genre"], visited_links=visited_links)
    #     visited_links |= set(book_links)
    #     #books_info, visited_links = scrapp_books_multiprocess(genre=genre["genre"], visited_links=visited_links, num_threads=16)
    #     save_books(book_links, genre='links_'+genre["genre"])
    
    # Get every book by the URL
    fileFormat = r'books_links_*.json'
    all_visited_categories = list(pathlib.Path(data_path).glob(fileFormat))

    for file_path in tqdm(all_visited_categories):
        with open(file_path, 'r') as f:
            book_urls = json.load(f)

        genre = re.match(r'books_links_(\S+).json', file_path.name).group(1) 
        max_workers = 100
        books_info = []

        for idx in tqdm(list(range(0,len(book_urls), max_workers)),desc=f'Getting {genre} books', leave=False):
            links_from_file = book_urls[idx:idx+max_workers]
            previous_down_books = dict()

            # See what are the urls that we still need to download
            try:
                with open(data_path+"books_info_"+genre+".json", 'r') as f:
                    previous_down_books = json.load(f)
                f.close()
                links = [l for l in links_from_file if l not in list(previous_down_books.keys())]
                if len(previous_down_books) >= MAX_NUM_BOOKS:
                    print(f"All set with {genre} genre! ^.^")
                    break

            except FileNotFoundError:
                links = links_from_file

            # Run get_book_info() function in thread
            with ThreadPoolExecutor(max_workers=max_workers) as executor:
                books_info = list(executor.map(get_book_info, links))
                print(books_info)
                books_info += books_info

            # Save the book info after each max number of thread workers
            thread_to_save = {links[i]: books_info[i] for i in range(len(links)) if books_info[i]["author"] != None}
            merg_to_save = thread_to_save | previous_down_books
            save_books(merg_to_save, genre='info_'+genre)

            # Break if it was not able to download a lot of files
            if len(thread_to_save) < max_workers and len(links) < 99:
                print("deu_merda")
                break
        
                

if __name__ == "__main__":
    main()
