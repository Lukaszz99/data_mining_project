class PrefixSpan:
    def __init__(self, sequences, min_supp=0.1, max_pattern_length=10):
        """
        Init class for PrefixSpan. Initialize all necessary variables.
        :param sequences: 3D list of words
        :param min_supp: Normalized support (0 - 1)
        :param max_pattern_length: Max lenght of pattern to find
        """

        min_supp = min_supp * len(sequences)
        self.placeholder = '_'

        freq_seq = self._perform_prefix_span(
            self.SequencePattern([], None, max_pattern_length, self.placeholder),
            sequences, min_supp, max_pattern_length)

        self.freq_seq = PrefixSpan.FreqSequences(freq_seq)

    @staticmethod
    def train(sequences, min_supp=0.1, max_pattern_length=10):
        return PrefixSpan(sequences, min_supp, max_pattern_length)

    def get_freq_seq(self):
        return self.freq_seq

    class FreqSequences:
        def __init__(self, fs):
            self.fs = fs

        def collect(self):
            return self.fs

    class SequencePattern:
        def __init__(self, sequence, support, max_pattern_length, place_holder):
            self.place_holder = place_holder
            self.sequence = []
            for s in sequence:
                self.sequence.append(list(s))
            self.freq = support

        def append(self, p):
            if p.sequence[0][0] == self.place_holder:
                first_e = p.sequence[0]
                first_e.remove(self.place_holder)
                self.sequence[-1].extend(first_e)
                self.sequence.extend(p.sequence[1:])
            else:
                self.sequence.extend(p.sequence)
                if self.freq is None:
                    self.freq = p.freq
            self.freq = min(self.freq, p.freq)

    def _check_pattern_lengths(self, pattern, max_pattern_length):
        for s in pattern.sequence:
            if len(s) > max_pattern_length:
                return False
        return True

    def _perform_prefix_span(self, pattern, S, threshold, max_pattern_length):
        patterns = []

        if self._check_pattern_lengths(pattern, max_pattern_length):
            f_list = self._frequent_items(S, pattern, threshold, max_pattern_length)

            for i in f_list:
                p = self.SequencePattern(pattern.sequence, pattern.freq, max_pattern_length, self.placeholder)
                p.append(i)
                if self._check_pattern_lengths(pattern, max_pattern_length):
                    patterns.append(p)

                p_S = self._build_projected_database(S, p)
                p_patterns = self._perform_prefix_span(p, p_S, threshold, max_pattern_length)
                patterns.extend(p_patterns)

        return patterns

    def _frequent_items(self, S, pattern, threshold, max_pattern_length):
        items = {}
        _items = {}
        f_list = []
        if S is None or len(S) == 0:
            return []

        if len(pattern.sequence) != 0:
            last_e = pattern.sequence[-1]
        else:
            last_e = []
        for s in S:

            # class 1
            is_prefix = True
            for item in last_e:
                if item not in s[0]:
                    is_prefix = False
                    break
            if is_prefix and len(last_e) > 0:
                index = s[0].index(last_e[-1])
                if index < len(s[0]) - 1:
                    for item in s[0][index + 1:]:
                        if item in _items:
                            _items[item] += 1
                        else:
                            _items[item] = 1

            # class 2
            if self.placeholder in s[0]:
                for item in s[0][1:]:
                    if item in _items:
                        _items[item] += 1
                    else:
                        _items[item] = 1
                s = s[1:]

            # class 3
            counted = []
            for element in s:
                for item in element:
                    if item not in counted:
                        counted.append(item)
                        if item in items:
                            items[item] += 1
                        else:
                            items[item] = 1

        f_list.extend([self.SequencePattern([[self.placeholder, k]], v, max_pattern_length, self.placeholder)
                       for k, v in _items.items()
                       if v >= threshold])
        f_list.extend([self.SequencePattern([[k]], v, max_pattern_length, self.placeholder)
                       for k, v in items.items()
                       if v >= threshold])

        f_list = [i for i in f_list if self._check_pattern_lengths(i, max_pattern_length)]

        sorted_list = sorted(f_list, key=lambda p: p.freq)
        return sorted_list

    def _build_projected_database(self, S, pattern):
        """
        suppose S is projected database base on pattern's prefix,
        so we only need to use the last element in pattern to
        build projected database
        """
        p_S = []
        last_e = pattern.sequence[-1]
        last_item = last_e[-1]
        for s in S:
            p_s = []
            for element in s:
                is_prefix = False
                if self.placeholder in element:
                    if last_item in element and len(pattern.sequence[-1]) > 1:
                        is_prefix = True
                else:
                    is_prefix = True
                    for item in last_e:
                        if item not in element:
                            is_prefix = False
                            break

                if is_prefix:
                    e_index = s.index(element)
                    i_index = element.index(last_item)
                    if i_index == len(element) - 1:
                        p_s = s[e_index + 1:]
                    else:
                        p_s = s[e_index:]
                        index = element.index(last_item)
                        e = element[i_index:]
                        e[0] = self.placeholder
                        p_s[0] = e
                    break
            if len(p_s) != 0:
                p_S.append(p_s)

        return p_S
