import os
from os import path
import argparse
from datetime import datetime
import json

from urllib.request import urlopen
from urllib.error import HTTPError
import bs4
import time
import pandas as pd

import regex as re
from goodreads_scraper.get_reviews import RATING_STARS_DICT


def scrape_books_from_user(id, max_page=None, shelf='read'):
    page = 1
    url_read = 'https://www.goodreads.com/review/list/' + \
        str(id) + '?page=' + str(page) + '&print=true&shelf=' + shelf

    source = urlopen(url_read)
    soup = bs4.BeautifulSoup(source, 'html.parser')

    time.sleep(2)

    page_nav = soup.find_all('div', id='reviewPagination')
    last_page = 1
    if page_nav:
        last_page = int(
            soup.find('div', id='reviewPagination').find_all('a')[-2].text)

    if max_page and max_page < last_page:
        last_page = max_page

    data = []
    for page in range(last_page):
        url = 'https://www.goodreads.com/review/list/' + \
            str(id) + '?page=' + str(page+1) + '&print=true&shelf=read'
        source = urlopen(url)
        soup = bs4.BeautifulSoup(source, 'html.parser')

        time.sleep(2)

        table = soup.find('table', id='books')
        table_body = table.find('tbody')

        rows = table_body.find_all('tr')
        for row in rows:
            title = row.find('td', attrs={'class': 'field title'})
            book_id = re.search(
                '\d+', path.split(title.find('a')['href'])[-1]).group()
            title = title.find('a')['title']

            rating = row.find('td', attrs={'class': 'field rating'})
            rating = rating.find_all('span', {'class': 'staticStars'})[0]
            if rating.has_attr('title'):
                rating = rating['title']
                rating = RATING_STARS_DICT[rating]
            else:
                rating = None

            review_elem = row.find('td', attrs={'class': 'field review'}).find_all(
                'span')[-1]
            review = review_elem.text
            if review == 'None':
                review_id = None
            else:
              review_id = re.search('\d+', review_elem['id']).group()
            
            date_started = row.find(
                'td', attrs={'class': 'field date_started'})
            date_started = date_started.find(
                'span', {'class': 'date_started_value'})
            if date_started:
                date_started = date_started.text
            date_read = row.find('td', attrs={'class': 'field date_read'})
            date_read = date_read.find('span', {'class': 'date_read_value'})
            if date_read:
                date_read = date_read.text
            date_added = row.find('td', attrs={'class': 'field date_added'})
            date_added = date_added.find('span').text.lstrip().rstrip()

            data.append({'book_id': book_id, 'book_title': title, 'rating': rating, 'review_id': review_id,
                        'date_started': date_started, 'date_read': date_read, 'date_added': date_added})

    return data

def condense_users(users_directory_path):

    users = []
    
    # Look for all the files in the directory and if they contain "book-metadata," then load them all and condense them into a single file
    for file_name in os.listdir(users_directory_path):
        if file_name.endswith('.json') and not file_name.startswith('.') and file_name != "all_users.json" and "book-metadata" in file_name:
            _user = json.load(open(users_directory_path + '/' + file_name, 'r')) #, encoding='utf-8', errors='ignore'))
            users.append(_user)

    return users


def main(args):

    start_time = datetime.now()
    script_name = os.path.basename(__file__)

    parser = argparse.ArgumentParser()
    parser.add_argument('--user_ids_path', type=str)
    parser.add_argument('--output_directory_path', type=str)
    parser.add_argument('--format', type=str, action="store", default="json",
                        dest="format", choices=["json", "csv"],
                        help="set file output format")
    args = parser.parse_args(args)

    user_ids              = [line.strip() for line in open(args.user_ids_path, 'r') if line.strip()]
    users_already_scraped =  [file_name.replace('_user-read_list.json', '') for file_name in os.listdir(args.output_directory_path) if file_name.endswith('.json') and not file_name.startswith('all_books')]
    users_to_scrape       = [user_id for user_id in user_ids if user_id not in users_already_scraped]
    condensed_books_path   = args.output_directory_path + '/all_books'

    for i, user_id in enumerate(users_to_scrape):
        try:
            print(str(datetime.now()) + ' ' + script_name + ': Scraping ' + user_id + '...')
            print(str(datetime.now()) + ' ' + script_name + ': #' + str(i+1+len(users_already_scraped)) + ' out of ' + str(len(user_ids)) + ' users')

            books = scrape_books_from_user(user_id)
            # Add book metadata to file name to be more specific
            json.dump(books, open(args.output_directory_path + '/' + user_id + '_user-read_list.json', 'w'))

            print('=============================')

        except HTTPError as e:
            print(e)
            exit(0)


    books = condense_users(args.output_directory_path)
    if args.format == 'json':
        json.dump(books, open(f"{condensed_books_path}.json", 'w'))
    elif args.format == 'csv':
        json.dump(books, open(f"{condensed_books_path}.json", 'w'))
        book_df = pd.read_json(f"{condensed_books_path}.json")
        book_df.to_csv(f"{condensed_books_path}.csv", index=False, encoding='utf-8')
        
    print(str(datetime.now()) + ' ' + script_name + f':\n\n🎉 Success! All users scraped. 🎉\n\nUser read list have been output to /{args.output_directory_path}\nGoodreads scraping run time = ⏰ ' + str(datetime.now() - start_time) + ' ⏰')



if __name__ == '__main__':
    main()
