import json
import pandas as pd
import os
import sys
import yaml


def load_scores(type_, dir_):
    if type_ == 'gsp':
        scores = list()
        # get all json files
        for f_ in [k for k in os.listdir(dir_) if 'lvl' in k]:
            with open(os.path.join(dir_, f_)) as f:
                tmp_ = json.load(f)
            if len(tmp_) > 0:
                for u in tmp_:
                    scores.append([u[0], u[1]])

        return scores

    elif type_ == 'prefixspan':
        scores = list()
        with open(os.path.join(dir_, 'output.txt')) as f:
            lines = f.readlines()

        lines = [eval(line.replace("\n", '')) for line in lines]
        for line in lines:
            scores.append([line[0], line[1]])

        return scores

    else:
        raise ValueError('CO TO ZA TYP MORDO?')


def main(output_directory: str):
    # get current directory
    current_dir = os.path.abspath(os.path.dirname(sys.argv[0]))
    output_root = os.path.join(current_dir, output_directory)

    # get all dirs inside output
    output_dirs = [x[0] for x in os.walk(output_root)][1:]

    # for every output dir check for config.yaml and results files
    # create list with these values:
    # [algorithm, directory_name, support, max_seq, max_trans, max_items, total_items, total_time, peak_memory, file with scores]
    # if any value is unknown insert null

    res_list = list()
    for out_dir in output_dirs:
        try:
            # load config data
            with open(os.path.join(out_dir, 'config.yaml')) as f:
                c = yaml.safe_load(f)

            # load results.json
            with open(os.path.join(out_dir, 'results.json')) as f:
                r = json.load(f)

            # check if memory key exists
            peak_memory = None
            try:
                peak_memory = r['total_memory'][1]
            except (KeyError, ValueError, TypeError, IndexError):
                pass

            dir_name = c['output']['out_directory'].split('/')[1]
            type_ = 'gsp'
            try:
                type_ = c['type']
            except KeyError:
                pass
            supp = c[type_]['min_supp_norm']

            ds = 'gsp'
            if 'max_seq' in c['dataset'].keys():
                ds = 'dataset'

            # load scores
            scores = load_scores(type_, out_dir)

            # combine data
            res_list.append(
                [type_, dir_name, supp, c[ds]['max_seq'], c[ds]['max_transactions'],
                 c[ds]['max_items'], r['time'], peak_memory, scores
                 ]
            )

        except FileNotFoundError:
            continue

    df_res = pd.DataFrame(res_list, columns=['algorithm', 'dir_name', 'support', 'max_seq', 'max_trans', 'max_items',
                                             'time', 'peak_memory', 'scores'])

    df_res = df_res.explode('scores')
    df_res[['seq', 'score']] = pd.DataFrame(df_res['scores'].tolist(), index=df_res.index)
    df_res = df_res.drop(columns=['scores'])
    df_res.to_csv('results.csv', index=False)


if __name__ == '__main__':
    main(output_directory='output')
