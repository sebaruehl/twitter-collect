import twitter
import configparser
import time
import datetime
import logging
import mysql.connector as mariadb

from . import repeated_timer

config_parser = configparser.RawConfigParser()
config_file_path = '../config/rest.conf'
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

LOG_FILE = config_parser.get('logging', 'file')

USER_TO_TRACK = config_parser.get('user', 'user_to_track')

MAX_CURRENT = config_parser.getint('rest', 'max_current_tweets')
DEAD_TIME = config_parser.getint('rest', 'dead_time')


# logging to file
logger = logging.getLogger('rest_tracking')
logger.setLevel(logging.DEBUG)
logger_file = logging.FileHandler(LOG_FILE)
logger_file.setLevel(logging.DEBUG)
logger.addHandler(logger_file)


api = twitter.Api(CONSUMER_KEY,
                  CONSUMER_SECRET,
                  ACCESS_TOKEN,
                  ACCESS_TOKEN_SECRET,
                  application_only_auth=True)


user_ids = USER_TO_TRACK.split(',')
pool = dict()
to_stop = []


def check_retweet(tweet_id):
    global to_stop
    current_ts = time.time() - 61  # not sure if loosing some retweets here
    retweets = api.GetRetweets(statusid=tweet_id, count=100)

    if len(retweets) > 0:
        db_conn = mariadb.connect(user=MARIA_USER, password=MARIA_PASSWORD, host=MARIA_HOST, database=MARIA_DATABASE)
        db = db_conn.cursor()

        i = 0
        while i < len(retweets) and retweets[i].created_at_in_seconds > current_ts:
            logger.info("New retweet of " + str(tweet_id) + ".")
            cur = retweets[i]
            t_id = cur.id
            tweet_ts = cur.created_at_in_seconds
            tweet_created_at = datetime.datetime.utcfromtimestamp(tweet_ts).strftime('%Y-%m-%d %H:%M:%S')
            tweet_uname = cur.user.screen_name
            tweet_uid = cur.user.id
            tweet_ufol = cur.user.followers_count
            tweet_oid = cur.retweeted_status.id
            tweet_ouid = cur.retweeted_status.user.id
            tweet_oretw = cur.retweeted_status.retweet_count
            db.execute("insert into %s values(%%s,%%s,%%s,%%s,%%s,%%s,%%s,%%s,%%s);" % TABLE_RETWEETS, (
                t_id, tweet_uname, tweet_uid, tweet_ufol, tweet_created_at, tweet_ts, tweet_oid, tweet_ouid, tweet_oretw
            ))
            i += 1

        if retweets[0].created_at_in_seconds < current_ts - DEAD_TIME * 60:
            to_stop.append(tweet_id)
            logger.info("Removed %i from queue." % tweet_id)
        db_conn.commit()
        db_conn.close()


def check_timeline():
    global user_ids
    global pool
    global MAX_CURRENT
    if len(pool) <= MAX_CURRENT:
        logger.info("Timeline check: Scanning for new tweets.")
        current_ts = time.time() - 60
        db_conn = mariadb.connect(user=MARIA_USER, password=MARIA_PASSWORD, host=MARIA_HOST, database=MARIA_DATABASE)
        db = db_conn.cursor()
        for uid in user_ids:
            timeline = api.GetUserTimeline(user_id=uid, count=50, include_rts=False, exclude_replies=True)
            if len(timeline) > 0:
                if timeline[0].created_at_in_seconds > current_ts:
                    tweet_id = timeline[0].id
                    if tweet_id in pool:
                        continue
                    tweet_text = timeline[0].text
                    tweet_ts = timeline[0].created_at_in_seconds
                    tweet_created_at = datetime.datetime.utcfromtimestamp(tweet_ts).strftime('%Y-%m-%d %H:%M:%S')
                    tweet_uname = timeline[0].user.screen_name
                    tweet_ufol = timeline[0].user.followers_count
                    db.execute("insert into %s values(%%s,%%s,%%s,%%s,%%s,%%s,%%s);" % TABLE_TWEETS, (
                        tweet_id, tweet_text, tweet_uname, uid, tweet_ufol, tweet_created_at, tweet_ts
                    ))
                    job = repeated_timer.RepeatedTimer(60, check_retweet, tweet_id)
                    pool[tweet_id] = job
                    logger.info("Timeline check: Found new tweet to track, current tweets in queue: " + str(len(pool)))
                    if len(pool) > MAX_CURRENT:
                        break
        db_conn.commit()
        db_conn.close()
    else:
        logger.info("Timeline check: Queue is full.")


def stop_job():
    global to_stop
    global pool

    if len(to_stop) > 0:
        for job in to_stop:
            pool[job].stop()
            logger.info("Stopped thread for %i." % job)
            del pool[job]
        to_stop = []


check_timeline_thread = repeated_timer.RepeatedTimer(60, check_timeline)
stop_job_thread = repeated_timer.RepeatedTimer(5, stop_job)

try:
    while True:
        time.sleep(30)
finally:
    check_timeline_thread.stop()
