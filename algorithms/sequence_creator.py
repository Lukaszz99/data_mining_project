import pandas as pd
import json
from collections import defaultdict
import os


def main(main_path, outfile):
    dfs = list()
    for f in [k for k in os.listdir(main_path) if '.csv' in k]:
        tmp_df = pd.read_csv(os.path.join(main_path, f))
        dfs.append(tmp_df)

    df = pd.concat(dfs)
    dd = defaultdict(lambda: list())

    for record in df[['text', 'time_window']].to_records():
        dd[record[2]].append(eval(record[1]))

    seq = list()
    for k, v in dd.items():
        seq.append(v)

    with open(os.path.join(main_path, outfile), "w", encoding='utf-8') as f:
        json.dump(seq, f, indent=4)


if __name__ == "__main__":
    main(main_path="/dataset", outfile="sequences.json")
