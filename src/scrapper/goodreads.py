import re
from typing import Any, Dict, List, Union
from bs4 import BeautifulSoup

import requests
import time
import random

ROOT_URL = 'https://www.goodreads.com/'


def get_book_info(url: str) -> Dict[str, Any]:
    """Extract information from Book.

    Args:
        url (str): Url of book.

    Returns:
        Dict[str, Any]: Extracted information.
    """   
    response = requests.get(url)
    soup = BeautifulSoup(response.content, 'html.parser')

    title, author = soup.find('title').string.split('by')
    image_url = soup.find('meta', property='og:image')['content']
    isbn13 = soup.find('meta', property='books:isbn')['content']
    num_pages = soup.find('meta', property='books:page_count')['content']
    avg_rating = soup.find('span', {'itemprop': 'ratingValue'}).string.split('\n')[1].strip()
    num_ratings = soup.find('meta', {'itemprop': 'ratingCount'}).string.split('\n')[1].strip()
    num_reviews = soup.find('meta', {'itemprop': 'reviewCount'}).string.split('\n')[1].strip()
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


def get_books(genre: str, min_sleep: float=0.5, max_sleep: float=1.5) -> List[Dict[str, Any]]:
    URL = "shelf/show/{genre}?page={page}"
    page = 1 
    books = []

    url = ROOT_URL + URL.format(genre=genre, page=page)
    html = requests.get(url).content
    data = BeautifulSoup(html, 'html.parser')

    number_books = data.select_one('div[class=leftContainer] > div[class=mediumText] > span[class=smallText]').string
    max_number_books = int(re.search(r'Showing \d{1,3}-\d{1,3} of (\d+(,\d+)?)', number_books).group(1).replace(',',''))

    while max_number_books > 0:
        all_books = data.select('div[class=leftContainer] > div[class=elementList]')
        for book in all_books:
            url_extension = book.find("a", {"class":"bookTitle"})['href']
            book_url = ROOT_URL + url_extension
            book_info = get_book_info(book_url)
            books.append(book_info)

            max_number_books -= 1
        
        sleep = random.uniform(min_sleep, max_sleep)
        time.sleep(sleep)
        
        page += 1
        url = ROOT_URL + URL.format(genre=genre, page=page)
        html = requests.get(url).content
        data = BeautifulSoup(html, 'html.parser')

    return books
