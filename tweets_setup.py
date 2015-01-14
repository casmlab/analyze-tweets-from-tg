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
    hedges = ast.literal_eval(config.get("Terms", "hedges"))
    
    return db_params, mysql_table, key_terms, key_users, hedges

# DATA GETTING/FORMATTING

# default data is a dictionary with keys id, day, text 
# optional: specify a user to limit tweets
# dumps MySQL data to a JSON file
def make_tweets_json(conn, user="All", table="tweet"):
    logging.info("Getting tweets...") 
    
    # build the query
    if user == "All":
        query = "SELECT `tweet_id_str` as `tweet_id`, `day`, `text`, `from_user` as `user_id`, `from_user_name` as `user_name` FROM %s " % table
    else:
        query = 'SELECT `tweet_id_str` as `id`, `day`, `text`, `from_user` FROM %s WHERE lower(`from_user_name`) = \'%s\'' % (table, user)
        
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
    
# create a dictionary of day:text or user:text where text is a concatenation of all tweets from that day/user
# dump it to json
def pivot_tweets(table, pivot_field):
    logging.info("Creating list of %s:text dictionaries..." % pivot_field) 
    json_data = table + ".json"
    json_data = open(json_data, 'r')
        
    if pivot_field == 'day':
        current = '2014-10-17'
    elif pivot_field in ('user_id', 'user_name'):
        current = ''
    else:
        logging.error("Unrecognized pivot type: %s" % pivot_field)
        return
        
    # tweets aren't sorted, so do that first

    tweets = json.load(json_data)
    tweets = sorted(tweets,key=lambda x:x[pivot_field])
        
    # loop through the sorted tweets and make day/user:text entries
    pivoted_tweets = {}
    current_tweets = ''
    for tweet in tweets:
        # if we're still working on the same day/user as the last tweet
        # should rewrite to use isoformat dates instead of str
        if current == tweet[pivot_field]:
            current_tweets += " " + tweet['text']
        else: # if we've finished tweets for that day/user, move on to the next one
            # first, write the entry for the day/user that's done
            pivoted_tweets[current] = current_tweets
            current = tweet[pivot_field]
            current_tweets = tweet['text']
        # when we're done looping, write the entry for the last day/user
        pivoted_tweets[current] = current_tweets
    output_file = table + "_by_" + pivot_field + ".json"
    with open(output_file, 'w') as f: 
        json.dump(pivoted_tweets, f)
    logging.info("Dumped data to %s." % output_file) 
        
# MAIN
def main():
    logging.info("Getting started with main SETUP function...")
    try:
        logging.info("Getting config values...")
        db_params, mysql_table, key_terms, key_users, hedges = get_config()
    except:
        logging.error("Couldn't get config values. Exiting.")
        sys.exit(0)

    # get a database connection and analyze the data
    try :
        logging.info("Connecting to DB...") 
        conn = connect(db_params)

        # get the data into forms we can work with
        all_tweets = make_tweets_json(conn, table=mysql_table)
        pivot_tweets(mysql_table, 'day')
        # pivot_tweets(mysql_table, 'user_id')
        pivot_tweets(mysql_table, 'user_name')

    except sql.Error as err :
        logging.error(err)

    else:
        logging.info("Closing connection and cleaning up.")
        conn.close()
        logging.info("DONE SETTING UP.")

# Call the main function
if __name__ == '__main__' :
    main()
