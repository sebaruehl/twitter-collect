drop table tweets;
create table tweets (
  id bigint not null,
  text varchar(1000),
  user_name varchar(255),
  user_id bigint,
  user_follower_count int,
  created_at datetime,
  created_at_in_seconds int
);

drop table retweets;
create table retweets (
  id bigint not null,
  user_name varchar(255),
  user_id bigint,
  user_follower_count int,
  created_at datetime,
  created_at_in_seconds int,
  original_tweet_id bigint,
  original_tweet_user_id bigint,
  original_tweet_retweet_count int
);