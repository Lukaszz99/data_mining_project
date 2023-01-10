import copy
from operator import neg
import json


class GSP:
    def __init__(self, dataset, log_level, output_file):
        self._dataset = dataset
        self._log_level = log_level
        self._out = output_file

    def search(self, support_norm):
        patterns = []

        # min_sup now is an integer
        min_sup = support_norm * len(self._dataset)

        # make the first pass over the sequence database to yield all the 1-element frequent subsequences
        items = sorted(set([item for sequence in self._dataset
                            for event in sequence
                            for item in (event[1] if isinstance(event, tuple) else event)]))

        single_item_sequences = [[[item]] for item in items]
        single_item_counts = [(s, self._count_support(self._dataset, s)) for s in single_item_sequences]
        single_item_counts = [(i, count) for i, count in single_item_counts if count >= min_sup]

        patterns.append(single_item_counts)

        if self._log_level > 0:
            print('Result for lvl 1: Done')
            with open(f"{self._out}/lvl1.json", 'w') as f:
                json.dump(patterns[0], f, sort_keys=False, indent=4)

        k = 1
        while patterns[k - 1]:
            # 1. candidate generation: merge pairs of frequent subsequences found in the
            # (k-1)th pass to generate candidate sequences that contain k items
            last_lvl_cands = [x[0] for x in patterns[k - 1]]
            cands_gen = self._gen_cands(last_lvl_cands)

            # 2. candidate pruning: prune candidate k-sequences that contain infrequent
            # (contiguous) (k-1)-subsequences (Apriori principle)
            cands_pruned = self._prune_cands(last_lvl_cands, cands_gen)

            # 3. support counting: make a new pass over the sequence database to find
            # the support for these candidate sequences
            cands_counts = [(s, self._count_support(self._dataset, s)) for s in cands_pruned]

            # 4. candidate elimination: eliminate candidate k-sequences whose actual
            # support is less than `minsup`
            result_lvl = [(i, count) for i, count in cands_counts if count >= min_sup]

            if self._log_level > 0:
                print('Result for lvl ' + str(k + 1) + ': Done')
                with open(f"{self._out}/lvl{k+1}.json", 'w') as f:
                    json.dump(result_lvl, f, sort_keys=False, indent=4)

                if self._log_level > 1:
                    print('Candidates generated, lvl ' + str(k + 1) + ': ' + str(cands_gen))
                    print('Candidates pruned, lvl ' + str(k + 1) + ': ' + str(cands_pruned))

            patterns.append(result_lvl)
            k += 1

        # "flatten" overall
        patterns = patterns[:-1]
        patterns = [item for sublist in patterns for item in sublist]
        patterns.sort(key=lambda tup: (tup[1], neg(self._sequence_length(tup[0]))), reverse=True)

        return patterns

    def _count_support(self, dataset, cand_seq):
        """
        Computes the support of a sequence in a dataset
        """
        return sum(1 for seq in dataset if
                   self._is_subsequence([event[1] for event in seq] if isinstance(seq[0], tuple) else seq, cand_seq))

    def _is_subsequence(self, main_sequence, subsequence):
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

        return is_subsequence_recursive(subsequence.copy())

    def _sequence_length(self, sequence):
        """
        Computes the length of the sequence (sum of the length of the contained itemsets)
        """
        return sum(len(i) for i in sequence)

    def _gen_cands(self, last_lvl_cands):
        """
        Generates the set of candidates of length k from the set of frequent sequences with length (k-1)
        """
        k = self._sequence_length(last_lvl_cands[0]) + 1
        if k == 2:
            flat_short_cands = [item for sublist2 in last_lvl_cands for sublist1 in sublist2 for item in sublist1]
            result = [[[a, b]] for a in flat_short_cands for b in flat_short_cands if b > a]
            result.extend([[[a], [b]] for a in flat_short_cands for b in flat_short_cands])
            return result
        else:
            cands = []
            for i in range(0, len(last_lvl_cands)):
                for j in range(0, len(last_lvl_cands)):
                    new_cand = self._gen_cands_for_pair(last_lvl_cands[i], last_lvl_cands[j])
                    if not new_cand == []:
                        cands.append(new_cand)
            cands.sort()
            return cands

    def _gen_cands_for_pair(self, cand1, cand2):
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

    def _prune_cands(self, last_lvl_cands, cands_gen):
        """
        Prunes the set of (contiguous) candidates generated for length k given all frequent sequence of level (k-1).
        Acandidate k-sequence is pruned if at least one of its (k-1)-subsequences is infrequent.
        """
        return [cand for cand in cands_gen if
                all(x in last_lvl_cands for x in (self._gen_contiguous_direct_subsequences(cand)))]

    def _gen_contiguous_direct_subsequences(self, sequence):
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
