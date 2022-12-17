from nltk.corpus import stopwords
from nltk.stem.snowball import SnowballStemmer
from tqdm import tqdm
import pandas as pd
import re
import tweepy
import yaml
import nltk

nltk.download('stopwords')
nltk.download('punkt')


def main(configfile_path, time_window_width):
    """

    :param configfile_path:
    :param time_window_width:
    :return:
    """

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
    time_windows = [['2022-12-04T12:00:00.000Z', '2022-12-04T23:59:59.000Z'],
                    ['2022-12-05T00:00:00.000Z', '2022-12-05T23:59:59.000Z'],
                    ['2022-12-06T00:00:00.000Z', '2022-12-06T23:59:59.000Z'],
                    ['2022-12-07T00:00:00.000Z', '2022-12-07T23:59:59.000Z'],
                    ['2022-12-08T00:00:00.000Z', '2022-12-08T23:59:59.000Z'],
                    ['2022-12-09T00:00:00.000Z', '2022-12-09T23:59:59.000Z'],
                    ['2022-12-10T00:00:00.000Z', '2022-12-10T23:59:59.000Z']]

    query = '#twitter #elonmusk lang:en -is:retweet'
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

        df = df[['author_id', 'created_at', 'id', 'text', 'org', 'time_window']]

        df_file = f"musk_twitter_{start_time.split('T')[0]}.csv"
        df.to_csv(df_file, index=False)

        print(f"Saved {df_file}")


if __name__ == '__main__':
    main("access_config.yaml", time_window_width=6)
