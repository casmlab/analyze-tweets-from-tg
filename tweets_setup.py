### SETUP ENVIRONMENT
from __future__ import division

import ast
import collections
from ConfigParser import SafeConfigParser
from datetime import datetime
import json
import logging
import mysql.connector as sql
from mysql.connector import errorcode
import os
import requests
from requests import HTTPError, ConnectionError
import sys

reload(sys)
sys.setdefaultencoding("utf-8")

# setup logging
def start_log():
    log_file = os.environ.get('ANALYZE_TWEETS_LOG_FILE','analyze_tweets.log')
    logging.basicConfig(filename=log_file, level=logging.DEBUG, format='%(asctime)s %(message)s', datefmt='%m/%d/%Y %I:%M:%S %p')
    
start_log()
logging.info('STARTING SETUP')

# from http://stackoverflow.com/questions/11875770/how-to-overcome-datetime-datetime-not-json-serializable-in-python
def date_handler(obj):
    return obj.isoformat() if hasattr(obj, 'isoformat') else obj
    
# Connect to MySQL using config entries
def connect(db_params) :
    return sql.connect(**db_params)
    
def get_config():
    config = SafeConfigParser()
    script_dir = os.path.dirname(__file__)
    config_file = os.path.join(script_dir, 'settings.cfg')
    config.read(config_file)
    db_params = {
            'user' : config.get("MySQL","user"),
            'password' : config.get("MySQL","password"),
            'host' : config.get("MySQL","host"),
            'database' : config.get("MySQL","database"),
            'charset' : 'utf8',
            'collation' : 'utf8_general_ci',
            'buffered' : True
    }
    mysql_table = config.get("MySQL","table")
    key_terms = ast.literal_eval(config.get("Terms", "key_terms"))
    key_users = ast.literal_eval(config.get("Terms", "key_users"))
    
    return db_params, mysql_table, key_terms, key_users

# DATA GETTING/FORMATTING

# default data is a dictionary with keys id, day, text 
# optional: specify a user to limit tweets
# dumps MySQL data to a JSON file
def make_tweets_json(conn, user="All", table="tweets"):
    logging.info("Getting tweets...") 
    
    # build the query
    if user == "All":
        query = "SELECT `tweet_id_str` as `id`, `day`, `text` FROM %s " % table
    else:
        query = 'SELECT `tweet_id_str` as `id`, `day`, `text` FROM %s WHERE lower(`from_user_name`) = \'%s\'' % (table, user)
        
    # connect to database and get the data as a dictionary
    cursor = conn.cursor(dictionary=True)
    cursor.execute(query)
    tweets = cursor.fetchall()
    cursor.close()
    
    logging.info("Have tweets. Munging them.")
    
    tweet_dict = tweets
    
    for tweet in tweets:
        tweet['day'] = date_handler(tweet['day'])

    output_file = table + "." + "json"
    with open(output_file, 'w') as f: 
        json.dump(tweets, f)
    logging.info("Dumped %s tweets to %s." % (str(len(tweets)), output_file)) 
    
    return tweet_dict
    
# create a dictionary of day:text where text is a concatenation of all tweets from that day
# dump it to json
def tweets_by_day(table):
    logging.info("Creating list of day:text dictionaries...") 
    json_data = table + ".json"
    json_data = open(json_data, 'r')
    
    # tweets aren't sorted by day, so do that first

    tweets = json.load(json_data)
    tweets = sorted(tweets,key=lambda x:x['day'])
        
    curr_day = '2014-10-17'
    tweets_by_day = {}
    days_tweets = ''
    for tweet in tweets:
        # if we're still working on the same day as the last tweet
        # should rewrite to use isoformat dates instead of str
        if curr_day == str(tweet['day']):
            days_tweets += " " + tweet['text']
        else: # if we've finished tweets for that day, move on to the next one
            # first, write the dictionary entry for the day that's done
            tweets_by_day[curr_day] = days_tweets
            curr_day = str(tweet['day'])
            days_tweets = tweet['text']
        # when we're done looping, write the entry for the last day
        tweets_by_day[curr_day] = days_tweets
    output_file = table + "_by_day.json"
    with open(output_file, 'w') as f: 
        json.dump(tweets_by_day, f)
    logging.info("Dumped data to %s." % output_file) 
    
# MAIN
def main():
    logging.info("Getting started with main function...")
    try:
        logging.info("Getting config values...")
        db_params, mysql_table, key_terms, key_users = get_config()
    except:
        logging.error("Couldn't get config values. Exiting.")
        sys.exit(0)

    # get a database connection and analyze the data
    try :
        logging.info("Connecting to DB...") 
        conn = connect(db_params)

        # get the data into forms we can work with
        all_tweets = make_tweets_json(conn, table=mysql_table)
        tweets_by_day(mysql_table)

    except sql.Error as err :
        logging.error(err)

    else:
        logging.info("Closing connection and cleaning up.")
        conn.close()
        logging.info("DONE.")

# Call the main function
if __name__ == '__main__' :
    main()