import json
import yaml
from algorithms.gsp import GSP
from algorithms.spade import SPADE
import os
import sys
from typing import List
from statistics import median
from time import time


def load_dataset(file_path, config) -> List[List[List[str]]]:
    dataset_path = os.path.join(file_path, config['dataset']['path'])

    with open(dataset_path) as f:
        dataset = json.load(f)

    return dataset


def clean_dataset(dataset):
    new_dataset = list()

    for s in dataset:
        new_seq = list()
        for transaction in s:
            new_transaction = list()
            for i in transaction:
                if i != 'elonmusk' and i != 'twitter' and i != 'co' and i != 'elon' and i != 'musk' and i != 'https' and len(i) > 2 and i != 'twitterfil':
                    new_transaction.append(i)
            new_seq.append(new_transaction)
        new_dataset.append(new_seq)

    return new_dataset


def describe_dataset(dataset):
    transactions = [len(seq) for seq in dataset]
    items = list()
    total_items = 0
    for s in dataset:
        for transaction in s:
            items.append(len(transaction))
            total_items += len(transaction)

    print(f"# of sequences: {len(dataset)} Max nb of transactions in sequence: {max(transactions)}, "
          f"min: {min(transactions)}, median: {median(transactions)}. Max nb of items in transaction: {max(items)}, "
          f"min: {min(items)}, median: {median(items)}. Total nb of items: {total_items}")

    return total_items


def prepare_dataset(dataset, max_seq, max_transactions, max_items):
    dataset = dataset[:max_seq]
    dataset = [s[:max_transactions] for s in dataset]

    new_dataset = list()

    for s in dataset:
        new_transaction = list()
        for transaction in s:
            new_transaction.append(transaction[:max_items])
        new_dataset.append(new_transaction)

    tot_items = describe_dataset(new_dataset)
    return new_dataset, tot_items


def tokenize(dataset):
    last_token = 1

    token_dict = dict()
    new_dataset = list()

    for s in dataset:
        new_seq = list()
        for transaction in s:
            new_transaction = list()
            for i in transaction:
                if i in token_dict.keys():
                    new_transaction.append(token_dict[i])
                else:
                    token_dict[i] = last_token
                    last_token += 1
                    new_transaction.append(last_token)

            new_seq.append(new_transaction)
        new_dataset.append(new_seq)

    return new_dataset, token_dict


def main():
    file_path = os.path.abspath(os.path.dirname(sys.argv[0]))

    with open(os.path.join(file_path, 'config.yaml')) as f:
        config = yaml.safe_load(f)

    dataset = load_dataset(file_path, config)
    dataset = clean_dataset(dataset)
    describe_dataset(dataset)

    dataset, tot_items = prepare_dataset(dataset, config['dataset']['max_seq'], config['dataset']['max_transactions'],
                                         config['dataset']['max_items'])

    # dataset, token_dict = tokenize(dataset)

    # create directory for output files
    output_path = os.path.join(file_path, config['output']['out_directory'])
    if not os.path.exists(output_path):
        os.makedirs(output_path)
    elif os.path.exists(output_path):
        print('UWAGA, FOLDER ISTNIEJE, JEŻELI CHCESZ KONTYNUOWAĆ KLIKNIJ 1')
        if int(input()) == 1:
            onlyfiles = [f for f in os.listdir(output_path) if os.path.isfile(os.path.join(output_path, f))]
            for f in onlyfiles:
                os.remove(os.path.join(output_path, f))
            pass
        else:
            exit(15)

    # save config dict do output path
    with open(os.path.join(output_path, 'config.yaml'), 'w') as outfile:
        yaml.dump(config, outfile, default_flow_style=False)

    if config['type'] == 'gsp':
        s_ = time()
        gsp = GSP(dataset=dataset,
                  log_level=config['gsp']['log_level'],
                  output_file=output_path)
        gsp.search(support_norm=config['gsp']['min_supp_norm'])

        stop_ = time()
        tot_time = stop_ - s_
        print(tot_time)

    elif config['type'] == 'spade':
        s_ = time()

        spd = SPADE(dataset)
        df = spd.read_dataset()
        support_results = spd.spade(df, config['spade']['min_supp_norm'])

        stop_ = time()
        tot_time = stop_ - s_
        print(tot_time)

        support_results.to_csv(os.path.join(output_path, 'spade_output.csv'))

    else:
        print(f"UNKNOWN ALGORITHM: {config['type']}")
        exit(15)

    # save time for this task
    with open(os.path.join(output_path, 'results.json'), 'w') as f:
        data = {
            'tot_items': tot_items,
            'time': tot_time
        }
        json.dump(data, f, indent=4, sort_keys=False)


if __name__ == "__main__":
    main()
