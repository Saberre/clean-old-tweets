import sys
import json
import zipfile
import datetime

from requests_oauthlib import OAuth1Session

import config

PY3 = sys.version_info > (3,)
TWEET_INDEX_PATH = 'data/js/tweet_index.js'
TWITTER_API_VERIFY = 'https://api.twitter.com/1.1/account/verify_credentials.json'
TWITTER_API_DELETE = 'https://api.twitter.com/1.1/statuses/destroy/{0}.json?trim_user=false'

input_func = input if PY3 else raw_input


def load_zip(path):
    try:
        return zipfile.ZipFile(path, 'r')
    except:
        return None


def get_tweet_index(zip_obj):
    try:
        raw_str = zip_obj.read(TWEET_INDEX_PATH).decode('utf-8')
    except KeyError:
        return None
    obj = json.loads(raw_str[raw_str.index('['):])
    return sorted(obj, key=lambda x: '{0}{1:02d}'.format(x['year'], x['month']))


def get_tweets(zip_obj, tweets_path):
    raw_str = zip_obj.read(tweets_path).decode('utf-8')
    obj = json.loads(raw_str[raw_str.index('['):])
    return map(lambda x: x['id_str'], obj)


def print_formatted_index(index_list):
    for index in index_list:
        print("{0:>5} tweets on {1}/{2:02d}".format(index['tweet_count'], index['year'], index['month']))


def twitter_session():
    return OAuth1Session(config.CONSUMER_KEY,
                         config.CONSUMER_SECRET,
                         config.ACCESS_TOKEN,
                         config.ACCESS_TOKEN_SECRET)


def delete_tweet(session, tweet_id):
    return session.post(TWITTER_API_DELETE.format(tweet_id))

if __name__ == '__main__':
    zip_path = sys.argv[1]
    zip_object = load_zip(zip_path)
    if not zip_object:
        print('The path you\'ve specified is not a file or valid zip file.')
        exit(1)

    session = twitter_session()
    if session.get(TWITTER_API_VERIFY).status_code != 200:
        print('Your Twitter OAuth token is invalid. Please check config.py and try again.')
        exit(1)

    tweet_indices = get_tweet_index(zip_object)
    if not tweet_indices:
        print('The file you\'ve specified doesn\'t seem to be a valid Twitter archive.')
        exit(1)
    print_formatted_index(tweet_indices)

    while True:
        months_str = input_func('How many months do you want to keep (3)? ')
        if not months_str:
            months = 3
            break
        try:
            months = int(months_str)
            break
        except:
            continue
    target_month = datetime.date.today().replace(day=1)
    for i in range(months):
        target_month = target_month - datetime.timedelta(days=1)
        target_month = target_month.replace(day=1)

    for index in filter(lambda x: datetime.date(x['year'], x['month'], 1) <= target_month, tweet_indices):
        print('Deleting tweets posted in {0}/{1:02d}...'.format(index['year'], index['month']))
        tweet_ids = get_tweets(zip_object, index['file_name'])
        for tweet_id in tweet_ids:
            result = delete_tweet(session, tweet_id)
            if result.status_code != 200:
                print('Error while deleting tweet id {0}: {1}'.format(tweet_id, result.json()['errors'][0]['message']))
