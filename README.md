Analyze Tweets 
==============

Python scripts for analyzing tweets collected using
[TwitterGoggles](https://github.com/pmaconi/TwitterGoggles). The emphasis is
on language and language use trends.

## Before You Start 

You need to add a new column to the `tweets` table in your
MySQL database and set its values.

``` ALTER TABLE `tweets` ADD `day` DATE AFTER `created_at`;```

``` UPDATE `tweets` SET `day` = DATE(`created_at`);```

Note: you can use `created_at` if you don't have much data, but getting `day`
is much faster for >1M rows.

OPTIONAL: Set your ```ANALYZE_TWEETS_LOG_FILE``` environment variable. Default is 'analyze_tweets.log'.

## How does this work?

The scripts are separated into two files that accomplish setup tasks (e.g.,
get data from the server) and analysis tasks (e.g., calculated word
frequencies). ```tweets_setup.py``` produces JSON files that
```tweets_analysis.py``` then uses for the analysis. This is designed to speed
up getting data since MySQL is a bottleneck.

## Usage 

Set your variables in the config file (copy settings_example.cfg to
settings.cfg).

```python tweets_setup.py```

```python tweets_analysis.py```

## Output

```tweets_setup.py``` produces 2 JSON files:
- tweets.json
- tweets_by_day.json

Examples of the JSON files are in [/examples](examples).

```tweets_analysis.py``` produces 3 TXT files and 2 PNG files:
- lexical_diversity.txt - a table of lexical diversity scores by day
- word_count.txt - counts of words and unique words
- word_freq.txt - a comma-delimited file with words and frequencies
