from nltk.corpus import stopwords
from nltk.stem.snowball import SnowballStemmer
from tqdm import tqdm
import pandas as pd
import re
import tweepy
import yaml
import nltk
import os

nltk.download('stopwords')
nltk.download('punkt')


def main(configfile_path, output_folder, query, time_window_width):

    with open(configfile_path) as f:
        access_dict = yaml.safe_load(f)
        api_key = access_dict['api_key']
        api_key_secret = access_dict['api_key_secret']
        access_token = access_dict['access_token']
        access_token_secret = access_dict['access_token_secret']
        bearer_token = access_dict['bearer_token']

    st = SnowballStemmer('english')
    stop_words = set(stopwords.words('english'))

    def clean_text(x, st, sw):
        """
        Creates list of separate words from each input.
        :param x: input sentence
        :param st: SnowballStemmer instance
        :param sw: stop words
        :return:
        """
        x = x.lower()
        x = re.sub('[^a-zA-Z]', ' ', x)
        x = ' '.join(st.stem(text) for text in x.split() if text not in sw)

        return x.split(' ')

    # create api client
    # return dict to create easily dataframe
    v2_client = tweepy.Client(bearer_token=bearer_token, consumer_key=api_key, consumer_secret=api_key_secret,
                              access_token=access_token, access_token_secret=access_token_secret)

    # time windows that indicates start and end time of tweet creation time for each query
    # List of lists: [[start_time1, end_time1], [start_time2, end_time2], ...]
    time_windows = [['2022-12-22T16:00:00.000Z', '2022-12-22T23:59:59.000Z'],
                    ['2022-12-23T00:00:00.000Z', '2022-12-23T23:59:59.000Z'],
                    ['2022-12-24T00:00:00.000Z', '2022-12-24T23:59:59.000Z'],
                    ['2022-12-25T00:00:00.000Z', '2022-12-25T23:59:59.000Z'],
                    ['2022-12-26T00:00:00.000Z', '2022-12-26T23:59:59.000Z'],
                    ['2022-12-27T00:00:00.000Z', '2022-12-27T23:59:59.000Z'],
                    ['2022-12-28T00:00:00.000Z', '2022-12-28T23:59:59.000Z'],
                    ['2022-12-29T00:00:00.000Z', '2022-12-29T11:59:59.000Z']]


    for start_time, end_time in tqdm(time_windows):
        tweets = tweepy.Paginator(v2_client.search_recent_tweets,
                                  query=query,
                                  max_results=100,
                                  start_time=start_time,
                                  end_time=end_time,
                                  tweet_fields=['author_id', 'created_at', 'text', 'source', 'lang', 'geo'],
                                  user_fields=['name', 'username', 'location', 'verified'],
                                  expansions=['geo.place_id', 'author_id'],
                                  place_fields=['country', 'country_code']).flatten(limit=10000)

        data = list()
        for tweet in tweets:
            data.append(
                [tweet.author_id, tweet.created_at, tweet.id, tweet.text]
            )

        df = pd.DataFrame(data=data,
                          columns=['author_id', 'created_at', 'id', 'text']
                          )

        # data cleaning
        df['org'] = df['text']
        df['text'] = df['text'].apply(lambda x: clean_text(x, st, stop_words))
        df['timestamp'] = pd.to_datetime(df['created_at']).dt.tz_localize(None)
        df['dec_hour'] = df['timestamp'].apply(lambda x: x.day * 24 + x.hour)
        df['time_window'] = df['dec_hour'] // time_window_width
        df = df.astype({'time_window': 'int32'})

        df = df[['author_id', 'created_at', 'id', 'text', 'org', 'time_window']]

        df_file = f"{output_folder}/S-300_{start_time.split('T')[0]}.csv"
        df.to_csv(df_file, index=False)

        print(f"Saved {df_file}")


if __name__ == '__main__':
    main("access_config.yaml", output_folder='s-300', query='S-300 lang:en -is:retweet', time_window_width=0.25)
