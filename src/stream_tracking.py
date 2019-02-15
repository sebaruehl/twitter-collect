import twitter
import configparser
import datetime
import mysql.connector as mariadb

config_parser = configparser.RawConfigParser()
config_file_path = '../config/streaming.conf'
config_parser.read(config_file_path)

CONSUMER_KEY = config_parser.get('twitter', 'consumer_key')
CONSUMER_SECRET = config_parser.get('twitter', 'consumer_secret')
ACCESS_TOKEN = config_parser.get('twitter', 'access_token')
ACCESS_TOKEN_SECRET = config_parser.get('twitter', 'access_token_secret')

MARIA_USER = config_parser.get('db', 'maria_user')
MARIA_PASSWORD = config_parser.get('db', 'maria_password')
MARIA_DATABASE = config_parser.get('db', 'maria_database')
MARIA_HOST = config_parser.get('db', 'maria_host')

TABLE_TWEETS = config_parser.get('tables', 'table_tweets')
TABLE_RETWEETS = config_parser.get('tables', 'table_retweets')

USER_TO_TRACK = config_parser.get('user', 'user_to_track')

api = twitter.Api(CONSUMER_KEY,
                  CONSUMER_SECRET,
                  ACCESS_TOKEN,
                  ACCESS_TOKEN_SECRET)

db_conn = mariadb.connect(user=MARIA_USER, password=MARIA_PASSWORD, host=MARIA_HOST, database=MARIA_DATABASE,
                          charset='utf8mb4')
db_conn.autocommit = False
db = db_conn.cursor()

user_ids = USER_TO_TRACK.split(',')


tmp_insert_cnt = 0
for line in api.GetStreamFilter(follow=user_ids):
    try:
        tweet_id = line['id']
        tweet_ts = int(line['timestamp_ms']) / 1000.0  # take only seconds despite value given in ms
        tweet_created_at = datetime.datetime.utcfromtimestamp(tweet_ts).strftime('%Y-%m-%d %H:%M:%S')
        tweet_uname = line['user']['screen_name']
        tweet_uid = line['user']['id']
        tweet_ufol = line['user']['followers_count']

        if 'retweeted_status' in line:
            tweet_oid = line['retweeted_status']['id']
            tweet_ouid = line['retweeted_status']['user']['id']
            tweet_oretw = line['retweeted_status']['retweet_count']
            db.execute("insert into %s values(%%s,%%s,%%s,%%s,%%s,%%s,%%s,%%s,%%s);" % TABLE_RETWEETS, (
                tweet_id, tweet_uname, tweet_uid, tweet_ufol, tweet_created_at, tweet_ts, tweet_oid, tweet_ouid,
                tweet_oretw
            ))
        else:
            tweet_text = line['text']
            db.execute("insert into %s values(%%s,%%s,%%s,%%s,%%s,%%s,%%s);" % TABLE_TWEETS, (
                tweet_id, tweet_text, tweet_uname, tweet_uid, tweet_ufol, tweet_created_at, tweet_ts
            ))

        tmp_insert_cnt += 1

        if tmp_insert_cnt == 100:
            db_conn.commit()
            tmp_insert_cnt = 0
    except KeyError:
        continue
