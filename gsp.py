import re
import copy
import numpy as np
import pandas as pd
from operator import neg


def is_subsequence(main_sequence, subsequence):
    """
    Recursive method that checks if `subsequence` is a subsequence of `main_sequence`
    """

    def is_subsequence_recursive(subsequence_clone, start=0):
        """
        Function for the recursive call of is_subsequence
        """
        # check if empty: end of recursion, all itemsets have been found
        if not subsequence_clone:
            return True
        # retrieves element of the subsequence and removes is from subsequence
        first_elem = set(subsequence_clone.pop(0))
        # search for the first itemset...
        for i in range(start, len(main_sequence)):
            if set(main_sequence[i]).issuperset(first_elem):
                # and recurse
                return is_subsequence_recursive(subsequence_clone, i + 1)
        return False

    return is_subsequence_recursive(subsequence.copy())  # start recursion


def sequence_length(sequence):
    """
    Computes the length of the sequence (sum of the length of the contained itemsets)
    """
    return sum(len(i) for i in sequence)


def supports(sequence, cand_seq, max_span=np.inf, min_gap=0, max_gap=np.inf):
    for idx, event in enumerate(sequence):
        i = 0
        if set(event[1] if isinstance(event, tuple) else event).issuperset(cand_seq[i]):
            min_t = event[0] if isinstance(event, tuple) else idx
            i += 1

            # special case if cand_seq is a sequence of one element
            if i == len(cand_seq):
                return True

            prev_t = event[0] if isinstance(event, tuple) else idx

            for t, itemset in (sequence[idx + 1:] if isinstance(sequence[idx], tuple)
            else enumerate(sequence[idx + 1:], start=idx + 1)):

                # the min_gap constraint is violated
                if not t - prev_t > min_gap:
                    continue

                # the max_gap constraint is violated
                if not t - prev_t <= max_gap:
                    break

                # the max_span constraint is violated
                if t - min_t > max_span:
                    break

                if set(itemset).issuperset(cand_seq[i]):
                    i += 1

                # the sequence satisfies all the time constraints
                if i == len(cand_seq):
                    return True
    return False


def count_support(dataset, cand_seq):
    """
    Computes the support of a sequence in a dataset
    """
    return sum(1 for seq in dataset if
               is_subsequence([event[1] for event in seq] if isinstance(seq[0], tuple) else seq, cand_seq))


def gen_cands_for_pair(cand1, cand2):
    """
    Generates one candidate of length k from two candidates of length (k-1)
    """
    cand1_clone = copy.deepcopy(cand1)
    cand2_clone = copy.deepcopy(cand2)
    # drop the leftmost item from cand1:
    if len(cand1[0]) == 1:
        cand1_clone.pop(0)
    else:
        cand1_clone[0] = cand1_clone[0][1:]
    # drop the rightmost item from cand2:
    if len(cand2[-1]) == 1:
        cand2_clone.pop(-1)
    else:
        cand2_clone[-1] = cand2_clone[-1][:-1]

    # if the result is not the same, then we dont need to join
    if not cand1_clone == cand2_clone:
        return []
    else:
        new_cand = copy.deepcopy(cand1)
        if len(cand2[-1]) == 1:
            new_cand.append(cand2[-1])
        else:
            new_cand[-1].extend([cand2[-1][-1]])
        return new_cand


def gen_cands(last_lvl_cands):
    """
    Generates the set of candidates of length k from the set of frequent sequences with length (k-1)
    """
    k = sequence_length(last_lvl_cands[0]) + 1
    if k == 2:
        flat_short_cands = [item for sublist2 in last_lvl_cands for sublist1 in sublist2 for item in sublist1]
        result = [[[a, b]] for a in flat_short_cands for b in flat_short_cands if b > a]
        result.extend([[[a], [b]] for a in flat_short_cands for b in flat_short_cands])
        return result
    else:
        cands = []
        for i in range(0, len(last_lvl_cands)):
            for j in range(0, len(last_lvl_cands)):
                new_cand = gen_cands_for_pair(last_lvl_cands[i], last_lvl_cands[j])
                if not new_cand == []:
                    cands.append(new_cand)
        cands.sort()
        return cands


def gen_direct_subsequences(sequence):
    """
    Computes all direct subsequence for a given sequence.
    A direct subsequence is any sequence that originates from deleting exactly one item from any event in the original sequence.
    """
    result = []
    for i, itemset in enumerate(sequence):
        if len(itemset) == 1:
            seq_clone = copy.deepcopy(sequence)
            seq_clone.pop(i)
            result.append(seq_clone)
        else:
            for j in range(len(itemset)):
                seq_clone = copy.deepcopy(sequence)
                seq_clone[i].pop(j)
                result.append(seq_clone)
    return result


def gen_contiguous_direct_subsequences(sequence):
    """
    Computes all direct contiguous subsequence for a given sequence.
    """
    result = []
    for i, itemset in enumerate(sequence):
        # first or last element
        if i == 0 or i == len(sequence) - 1:
            if len(itemset) == 1:
                seq_clone = copy.deepcopy(sequence)
                seq_clone.pop(i)
                result.append(seq_clone)
            else:
                for j in range(len(itemset)):
                    seq_clone = copy.deepcopy(sequence)
                    seq_clone[i].pop(j)
                    result.append(seq_clone)
        else:  # middle element
            if len(itemset) > 1:
                for j in range(len(itemset)):
                    seq_clone = copy.deepcopy(sequence)
                    seq_clone[i].pop(j)
                    result.append(seq_clone)
    return result


def prune_cands(last_lvl_cands, cands_gen):
    """
    Prunes the set of (contiguous) candidates generated for length k given all frequent sequence of level (k-1).
    Acandidate k-sequence is pruned if at least one of its (k-1)-subsequences is infrequent.
    """
    return [cand for cand in cands_gen if
            all(x in last_lvl_cands for x in (gen_contiguous_direct_subsequences(cand)))]


def gsp(dataset, min_sup, verbose=False):
    """
    The Generalized Sequential Pattern (GSP) algorithm with time constraints.
    Computes the frequent sequences in a sequence dataset.

    Args:
        dataset: a list of sequences, for which the frequent (sub-)sequences are computed
        min_sup: the minimum support that makes a sequence frequent
        verbose: if True, additional information on the mining process are printed (i.e., results
                 for each level if is 1, candidates generated and pruned at each level if is 2)

    Returns:
        A list of tuples (s, c), where s is a frequent sequence and c is the count for that sequence
    """
    overall = []
    min_sup *= len(dataset)
    # make the first pass over the sequence database to yield all the 1-element frequent subsequences
    items = sorted(set([item for sequence in dataset
                        for event in sequence
                        for item in (event[1] if isinstance(event, tuple) else event)]))
    single_item_sequences = [[[item]] for item in items]
    single_item_counts = [(s, count_support(dataset, s)) for s in single_item_sequences]
    single_item_counts = [(i, count) for i, count in single_item_counts if count >= min_sup]
    overall.append(single_item_counts)
    if verbose > 0:
        print('Result, lvl 1: ' + str(overall[0]))
    k = 1
    while overall[k - 1]:
        # 1. candidate generation: merge pairs of frequent subsequences found in the
        # (k-1)th pass to generate candidate sequences that contain k items
        last_lvl_cands = [x[0] for x in overall[k - 1]]
        cands_gen = gen_cands(last_lvl_cands)
        # 2. candidate pruning: prune candidate k-sequences that contain infrequent
        # (contiguous) (k-1)-subsequences (Apriori principle)
        cands_pruned = prune_cands(last_lvl_cands, cands_gen)
        # 3. support counting: make a new pass over the sequence database to find
        # the support for these candidate sequences
        cands_counts = [(s, count_support(dataset, s)) for s in cands_pruned]
        # 4. candidate elimination: eliminate candidate k-sequences whose actual
        # support is less than `minsup`
        result_lvl = [(i, count) for i, count in cands_counts if count >= min_sup]
        if verbose > 0:
            print('Result, lvl ' + str(k + 1) + ': ' + str(result_lvl))
            if verbose > 1:
                print('Candidates generated, lvl ' + str(k + 1) + ': ' + str(cands_gen))
                print('Candidates pruned, lvl ' + str(k + 1) + ': ' + str(cands_pruned))
        overall.append(result_lvl)
        k += 1
    # "flatten" overall
    overall = overall[:-1]
    overall = [item for sublist in overall for item in sublist]
    overall.sort(key=lambda tup: (tup[1], neg(sequence_length(tup[0]))), reverse=True)
    return overall



dataset = [
    [['A', 'B'], ['C'], ['F','G'],['G'],['E']],
    [['A','D'],['C'],['B'], ['A','B','E','F']],
    [['A'],['B'],['F','G'],['E']],
    [['B'],['F','G']]
]

gsp(dataset, 0.4, 1)