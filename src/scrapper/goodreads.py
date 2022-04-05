import re
from tkinter import image_names
from typing import Any, Dict, List, Union
from bs4 import BeautifulSoup

import requests


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
    URL = "https://www.goodreads.com/genres/list?page={page}"
    number_regex = re.compile(r'\d+[,\d{3}]*')
    genre_list = []

    next_url = "1" 
    while "next" not in  next_url:
        url = URL.format(page=next_url)
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