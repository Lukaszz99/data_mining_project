import pandas as pd
import os
import re


def main(path_to_csv):
    """

    :param path_to_csv: Path to folder containing all .csv files
    :return:
    """
    files = [os.path.join(path_to_csv, file) for file in os.listdir(path_to_csv) if '.csv' in file]
    list_df = list()
    for f in files:
        tmp_df = pd.read_csv(f)
        list_df.append(tmp_df)

    df = pd.concat(list_df)

    # cast tweet creation time to datetime
    df['created_at'] = pd.to_datetime(df['created_at'], format="%Y-%m-%dT%H:%M:%S.%f", errors='coerce')

    times = df.created_at
    df['time_group'] = times.dt.day * 10 + times.dt.hour // 6

    df['text'] = df['text'].apply(lambda x: x.split(' '))
    df['text'] = df['text'].apply(lambda x: [re.sub('[^a-zA-Z0-9 \n\.]', ' ', k) for k in x])
    df['text'] = df['text'].apply(lambda x: [k for k in x if len(k) > 2])
    print('a')


if __name__ == "__main__":
    main("/home/lsaw/studia/med/data_mining_project/dataset")
