'''
Schedule this script to be run one time every day until enough data has been imported.
'''

import datetime
import http.client
import urllib.parse
import json
from sqlalchemy import create_engine
from sqlalchemy.engine import URL
from sqlalchemy import text

# Takes a date in string format 'yyyy-mm-dd', and an integer and
# returns a new date which is start_date with nr_of_days added.
def date_counter(start_date, nr_of_days):
    d = datetime.date(int(start_date[:4]), int(start_date[5:7]), int(start_date[8:10]))
    d += datetime.timedelta(days=nr_of_days)
    return d

# Connect to the SQL database.
connection_string = (
    "Driver=ODBC Driver 17 for SQL Server;"
    r"Server=XXX\SQLEXPRESS;"
    "Database=JS_DB;"
    "Trusted_Connection=yes;"
)

connection_url = URL.create(
    "mssql+pyodbc",
    query={"odbc_connect": connection_string}
)

engine = create_engine(connection_url)

# Connect to the API.
conn = http.client.HTTPSConnection('api.thenewsapi.com')

# Query the min date of articles in the database table and calculate the start date of the API query
# which is 32 days before the min date.
with engine.connect() as connection:
    results = connection.execute(text("SELECT MIN(published_at) FROM thenewsapi")).fetchall()

min_date = results[0].__getitem__(0)
start_date = min_date - datetime.timedelta(days=32)

# Add a comment to be inserted in the comment column in the SQL table.
comment = "manual run of full script"

# For loop which makes one API call per iteration and inserts the response data in the database table.
# Range 32 means it gets data for 32 days. Those days are the 32 days before the min date in the table.
for i in range(32):
    params = urllib.parse.urlencode({
        'api_token': 'XXX',
        'categories': 'business',
        'language': 'en',
        'limit': 3,
        'published_on': date_counter(str(start_date), i)  # One date for each iteration in the 32 days range.
        })

    conn.request('GET', '/v1/news/all?{}'.format(params))
    res = conn.getresponse()

    # Convert the API response from json to dict.
    data = res.read()
    data_dict = json.loads(data)

    # The 'data' key is a list of dictionaries, each dictionary is one article.
    # For each article, insert its content into the SQL-table.
    with engine.connect() as connection:
        for article in data_dict['data']:
            connection.execute(text("INSERT INTO thenewsapi (uuid, title, description, snippet, language, published_at, source, categories, comment) \
                        VALUES ('" + article['uuid'] + "', '"
                                    + article['title'].replace('"', '""').replace("'", "''") + "', '"
                                    + article['description'].replace('"', '""').replace("'", "''") + "', '"
                                    + article['snippet'].replace('"', '""').replace("'", "''") + "', '"
                                    + article['language'] + "', '"
                                    + article['published_at'] + "', '"
                                    + article['source'] + "', '"
                                    + str(article['categories']).replace("'", "''") + "', '"
                                    + comment + "')"))
            connection.commit()

    print(f'{i + 1} loops done')
