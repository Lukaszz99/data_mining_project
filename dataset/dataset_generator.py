import pandas as pd
import tweepy
import yaml


def main(configfile_path, hashtag):
    with open(configfile_path) as f:
        access_dict = yaml.safe_load(f)
        api_key = access_dict['api_key']
        api_key_secret = access_dict['api_key_secret']
        access_token = access_dict['access_token']
        access_token_secret = access_dict['access_token_secret']
        bearer_token = access_dict['bearer_token']

    # create api client
    # return dict to create easily dataframe
    v2_client = tweepy.Client(bearer_token=bearer_token, consumer_key=api_key, consumer_secret=api_key_secret,
                              access_token=access_token, access_token_secret=access_token_secret, return_type=dict)

    # time windows that indicates start and end time of tweet creation time for each query
    # List of lists: [[start_time1, end_time1], [start_time2, end_time2], ...]
    time_windows = [['2022-11-28T00:00:00.000Z', '2022-11-28T23:59:59.000Z'],
                    ['2022-11-29T00:00:00.000Z', '2022-11-29T23:59:59.000Z'],
                    ['2022-11-30T00:00:00.000Z', '2022-11-31T23:59:59.000Z']]

    query = f'#{hashtag} lang:en -is:retweet'
    for start_time, end_time in time_windows:
        tweets = tweepy.Paginator(v2_client.search_recent_tweets,
                                  query=query,
                                  max_results=100,
                                  start_time=start_time,
                                  end_time=end_time,
                                  tweet_fields=['author_id', 'created_at', 'text', 'source', 'lang', 'geo'],
                                  user_fields=['name', 'username', 'location', 'verified'],
                                  expansions=['geo.place_id', 'author_id'],
                                  place_fields=['country', 'country_code']).flatten(limit=5000)

        # returned object is a generator of dicts, so cast it to list
        df = pd.DataFrame(data=list(tweets),
                          columns=['author_id', 'created_at', 'lang', 'id', 'source', 'text']
                          )

        df.to_csv(f"{hashtag}_{start_time.split('T')[0]}.csv", index=False)


if __name__ == '__main__':
    main("access_config.yaml", hashtag='biden')
