Simple scripts for collecting tweets and their retweets using the [Twitter Stream API](https://developer.twitter.com/en/docs/tutorials/consuming-streaming-data.html).

The collected data is directly stored into a MariaDB.

Because it seemed like the streaming API was dropping retweets (collected retweets did not add up
to the numbers seen directly on Twitter) another approach was implemented using the REST Api.
Here rate limits lead to only being able to track a small subset of tweets and their retweets.

### Tracked data
Goal: Track all tweets and it retweets for specific users.

For every tweet the following meta data is collected:
- created at
- user name
- user id
- user follower count
- text

For every retweet:
- created at
- user name 
- user id
- user follower count
- original user name 
- original user id
- original user follower count 


### Setup
To setup a simple database the docker-compose file in the root directory can be used.

The tables can be created using the SQL statements form within setup_database.sql.

### Configuration
Rename the template file in the config directory to config.conf and fill in the required data.
When tracking using the REST-Api it is possible to configure how many current tweet should be tracked for retweets and
the time after which a tweet should be seen as dead. Because of rate limits it is only possible to track a small amount 
(~5) of tweets at the same time.

The users to track should be provided as a text file containing user id and user name for each user and line.


### Run
If configured correctly run the either stream or REST tracking through standard Python script execution.