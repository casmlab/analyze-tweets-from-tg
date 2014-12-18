### SETUP ENVIRONMENT
from __future__ import division

import collections
import json
import logging
import matplotlib
import matplotlib.pyplot as plt
import nltk
from nltk.corpus import stopwords
from nltk import stem
import numpy as np
import pandas as pd
from pandas.stats.api import ols
from tabulate import tabulate
import re
import sys

# import functions from setup file
import tweets_setup as ts

reload(sys)
sys.setdefaultencoding("utf-8")

# start logging
ts.start_log()
logging.info('STARTING ANALYSIS')

# HELPERS
def lexical_diversity(text):
    return len(set(text)) / len(text)
    
def percentage(count, total):
    return 100 * count / total
    
def ratio(count, total):
    return count / total
    
def tokenize_tweets(tweet_text, lower=False, stemming=False):
    tokens = nltk.word_tokenize(tweet_text)
    text = nltk.Text(tokens)
    
    # normalize tokens to lowercase
    if lower == True:
        text = [t.lower() for t in text]
    
    # stem tokens
    if stemming == True:
        # chose Lancaster stemmer because it's more aggressive
        # more info on stemmers: http://www.nltk.org/api/nltk.stem.html
        # easily compare stemmers: http://text-processing.com/demo/stem/
        lancaster = stem.lancaster.LancasterStemmer()
        text = [lancaster.stem(t) for t in text]
        
    return text
    
def get_numpy_array(data):
    return np.array(data)

## GET DATA

def get_json(table, by_day=False):
    if by_day == False:
        tweets_file = table + ".json"
    else: 
        tweets_file = table + "_by_day.json"
    logging.info("Getting data from %s" % tweets_file) 
    tweets_file = open(tweets_file, 'r')
    tweets = json.load(tweets_file)
    return tweets

## CHANGES OVER TIME

# dispersion plots for topic words
def disp_plot(tweets, terms):
    tweet_text = ''.join(tweets.values())
    text = tokenize_tweets(tweet_text)
    text.dispersion_plot(terms)
    
# Lexical Diversity

# create a table with the lexical diversity of tweets by day or user
def diversity_table(tweets):
    logging.info("Creating table of lexical diversity scores...")
    diversity = {}
    for key, tweet_text in tweets.iteritems():
        text = tokenize_tweets(tweet_text, lower=True, stemming=True)
        diversity[key] = lexical_diversity(text)
    od = collections.OrderedDict(sorted(diversity.items()))
    return od
    
# How common are the words we care about?

# calculate the ratio of each term to all the words used each day
def calc_term_ratio(tweets, key_terms, lower=True, stemming=True):
    logging.info("Calculating percentages of key terms...")
    ratios = []
    for key, tweet_text in tweets.iteritems():
        text = tokenize_tweets(tweet_text, lower, stemming)
        total = len(text)
        for term in key_terms:
            count = text.count(term)
            ratios.append([key, term, ratio(count, total)])
    return ratios

# show trends over time
def plot_trends(ratios, key_terms, outfile):
    logging.info("Plotting ratios...")
    d = get_numpy_array(ratios)
    df = pd.DataFrame(d, columns=("Date","Term","Ratio"))
    df['Date'] = pd.to_datetime(df['Date'])
    df['Term'] = df['Term'].astype('category')
    df['Ratio'] = df['Ratio'].astype('float')
    dStart = min(df['Date'])
    dEnd = min(df['Date'])
    df = df.pivot(index='Date', columns='Term', values="Ratio")

    plot = df.plot(kind='bar')
    # plt.show()
    fig = plt.gcf()
    DefaultSize = fig.get_size_inches()
    fig.set_size_inches( (DefaultSize[0]*4, DefaultSize[1]*4) )
    fig.savefig(outfile)

# Create list of lower case words
# define words as `stuff between whitespace(s)'
# \s+ --> match any whitespace(s)
def create_word_list(tweets, remove_stop_words="true"):
    logging.info("Making the word list...")
    tweet_text = ''.join(tweets.values())
    word_list = re.split('\s+', tweet_text.lower())
    if remove_stop_words:
        stops = set(stopwords.words("english"))
        filtered_words = [w for w in word_list if not w in stops]
        return filtered_words
    else:
        return word_list
        
# Create dictionary of word:frequency pairs
# by default, sorts dictionary by frequency (desc) 
def create_freq_dic(word_list, sort="frequency"):
    logging.info("Making the word frequency dictionary...")
    freq_dic = {}

    # Remove punctuation marks:
    punctuation = re.compile(r'[(.?!,":;\'\\`)]') 

    for word in word_list:
        # remove punctuation marks
        word = punctuation.sub("", word)
        # form dictionary
        try: 
            freq_dic[word] += 1
        except: 
            freq_dic[word] = 1

    # sort the dictionary
    if sort == "frequency":
        freq_dic = [(val, key) for key, val in freq_dic.items()]
        # sort by frequency
        freq_dic.sort(reverse=True)
    # if user specificied alphabetical sorting, do that instead
    elif sort == "alphabetical":
        freq_dic = freq_dic.items()
        freq_dic.sort()    

    return freq_dic
    
# print frequency dictionaries
def print_freq(freq_dic):
    str_freq = ""
    for freq, word in freq_dic:
        str_freq += word + "," + str(freq) + "\n"
    return str_freq

### SOCIAL NETWORKS - POWER

## MEASURES OF CENTRALITY

def main():
    logging.info("Starting main ANALYSIS function...")
    try:
        logging.info("Getting config values...")
        _, mysql_table, key_terms, key_users = ts.get_config()
    except:
        logging.error("Couldn't get config values. Exiting.")
        sys.exit(0)
        
    # get and analyze the data
    try :
                
        # GET THE DATA into forms we can work with
        all_tweets = get_json(mysql_table)     
        days = get_json(mysql_table, by_day=True)
    
        # do some ANALYSIS
        # Q: How diverse is the language being used?
        ld_file = open("lexical_diversity.txt","w")
        od = diversity_table(days)
        ld_file.write(tabulate(od.items(), headers=["Day", "Lexical Diversity"])) 
        ld_file.close()
        
        # Q: What are the most commonly used words?
        logging.info("Counting and sorting words...")
        word_list = create_word_list(days)
        word_count = len(word_list)
        freq_dic = create_freq_dic(word_list)
        unique_word_count = len(freq_dic)
    
        # store the word counts and sorted word-frequency pairs
        wc_file = open("word_count.txt","w")
        wc_file.write(str(word_count) + " words\n")
        wc_file.write(str(unique_word_count) + " unique words")
        wc_file.close()
        
        wf_file = open("word_freq.txt","w")
        wf_file.write(print_freq(freq_dic))
        wf_file.close()

        # Q: What are the trends over time for terms/users we care about?
        plot_trends(calc_term_ratio(days, key_terms),key_terms,"term_trends.pdf")
        plot_trends(calc_term_ratio(days, key_users, True, False),key_users,"user_trends.pdf")
    
        # NOTE: functions below are broken or aren't used for some other reason
        # disp_plot(days, key_terms)
        
        logging.info("DONE WITH ANALYSIS.")
    except IOError as e:
        logging.error("I/O error({0}): {1}".format(e.errno, e.strerror))
    except:
        err = sys.exc_info()[0] 
        logging.error("Something went very wrong: %s" % err)
        
# Call the main function
if __name__ == '__main__' :
    main()
