from datetime import datetime
import warnings
warnings.simplefilter(action='ignore', category=FutureWarning)

from typing import Tuple, Union
import pandas as pd
from pandasql import sqldf


class SPADE:
    def __init__(self, dataset):
        self._dataset = dataset

    def read_dataset(self):
        """
            This function reads into pandas DataFrame a dataset formatted as follows:
                -1 separates elements
                -2 separates sequences
                Item can contain one or more items"""
        sid = 0
        data = []

        for seq in self._dataset:
            sid = self._dataset.index(seq)
            for s in seq:
                eid = seq.index(s)
                for item in s:
                    data.append([sid, eid, repr(set(item))])

        return pd.DataFrame(data, columns=['SID', 'EID', 'Items'])

    def sequence_items_join(self, A, B) -> pd.DataFrame:
        return sqldf(f'''
        select B.SID, B.EID
        from A as A
        join B as B
        on
        B.SID == A.SID
        and
        B.EID > A.EID;
    ''')


    def event_items_join(self, A, B) -> pd.DataFrame:
        return sqldf(f'''
        select B.SID, B.EID
        from A as A
        join B as B
        on
        B.SID == A.SID
        and
        B.EID == A.EID;
    ''')


    def find_F1(self, df: pd.DataFrame, min_sup: int):
        """
        Finds frequent (support >= min_sup) items or 1-sequences,
        e.g. {A}, {B}, returns dataframe with these items and their support.
        """
        F1 = dict(tuple(df.groupby('Items')))
        atoms_series = df.groupby('Items')[
            'SID'].nunique()  # atoms_series is pd.Series where items=index and their support = values.
        atoms = pd.DataFrame({'Items': atoms_series.index, 'Support': atoms_series.values})
        supports = atoms.loc[atoms['Support'] >= min_sup]
        # prune
        for key in list(F1.keys()):
            if key not in supports['Items'].to_list():
                F1.pop(key, None)
        return supports, F1


    def find_F2(self, F1: dict, supports: pd.DataFrame, min_sup: int) -> Tuple[pd.DataFrame, dict]:
        sq2_ctr = set()
        item_tree = {}
        F1_list = list(F1.keys())
        F1_list = [eval(item) for item in F1_list]
        # print(F1_list)
        for i, item1 in enumerate(F1_list):
            item_lvl_list = {}
            for j in range(len(F1_list)):
                item2 = F1_list[j]
                # generate event items
                if i != j:
                    event_item = repr([set(sorted((item1).union(item2)))])
                    # print(f"event item {event_item}")
                    if not event_item in sq2_ctr:
                        event_item_df = self.event_items_join(F1[repr(item1)], F1[repr(item2)])
                        support_value = event_item_df['SID'].nunique()
                        if support_value >= min_sup:
                            supports = supports.append({'Items': event_item, 'Support': support_value}, ignore_index=True)
                            item_lvl_list[event_item] = event_item_df
                    sq2_ctr.add(event_item)
                # generate sequence items
                sq_item = repr([item1, item2])
                # print('sq_item', sq_item)
                if not sq_item in sq2_ctr:
                    sq_item_df = self.sequence_items_join(F1[repr(item1)], F1[repr(item2)])
                    support_value = sq_item_df['SID'].nunique()
                    if support_value >= min_sup:
                        supports = supports.append({'Items': sq_item, 'Support': support_value}, ignore_index=True)
                        item_lvl_list[sq_item] = sq_item_df
                sq2_ctr.add(sq_item)
            item_tree[repr([(set(sorted(item1)))])] = item_lvl_list
        return supports, item_tree


    def generate_for_equal_len(self, item1, item2, branch, control_list: set) -> Tuple[bool, list, pd.DataFrame] or Tuple[
        bool, list, list]:
        is_event = True
        for x, y in map(lambda x, y: (x, y), item1, item2):
            if x.intersection(y):
                continue
            else:
                is_event = False
                break
        if is_event:
            generated_item = [set(sorted(a.union(b))) for a, b in map(lambda x, y: (x, y), item1, item2)]
            if repr(generated_item) not in control_list:
                ev_df = self.event_items_join(branch[repr(item1)], branch[repr(item2)])
                return is_event, generated_item, ev_df
            return is_event, generated_item, pd.DataFrame()
        else:
            ev = [set(sorted(a.union(b))) for a, b in map(lambda x, y: (x, y), item1, item2)]
            sq1 = (item2 + [item1[-1]])
            sq2 = (item1 + [item2[-1]])
            if repr(sq2) not in control_list:
                sq2_df = self.sequence_items_join(branch[repr(item1)], branch[repr(item2)])
            else:
                sq2_df = None
            if repr(sq1) not in control_list:
                sq1_df = self.sequence_items_join(branch[repr(item2)], branch[repr(item1)])
            else:
                sq1_df = None
            if repr(ev) not in control_list:
                ev_df = self.event_items_join(branch[repr(item1)], branch[repr(item2)])
            else:
                ev_df = None
            return is_event, [ev, sq1, sq2], [ev_df, sq1_df, sq2_df]


    def generate_for_unequal_len(self, item1, item2, branch, control_list: set) -> Tuple[list, pd.DataFrame]:
        if len(item1) > len(item2):
            generated_item = item2 + [item1[-1]]
            if repr(generated_item) not in control_list:
                # print(branch[repr(item1)])
                sdf = self.sequence_items_join(branch[repr(item2)], branch[repr(item1)])
            else:
                sdf = None
            return generated_item, sdf
        elif len(item1) < len(item2):
            generated_item = item1 + [item2[-1]]
            if repr(generated_item) not in control_list:
                sdf = self.sequence_items_join(branch[repr(item1)], branch[repr(item2)])
            else:
                sdf = None
            return generated_item, sdf


    def find_remaining(self, item_tree: dict, supports: pd.DataFrame, min_sup: int) -> Tuple[pd.DataFrame, dict]:
        three_dict = {}
        crtl_lst = set()

        for branch in item_tree.values():
            for item1 in branch:
                item1 = eval(item1)
                three_dict[repr(item1)] = {}
                for item2 in branch:
                    item2 = eval(item2)
                    if item1 == item2:
                        continue
                    if len(item1) == len(item2):
                        # event with event PB with PD should give: PBD
                        # seq with seq P->A with P->F should give: P->AF, P->A->F, P->F->A
                        # print(f"Item1: {item1}\nItem2: {item2}")
                        is_event, generated, sdfs = self.generate_for_equal_len(item1, item2, branch, crtl_lst)
                        if is_event:
                            if repr(generated) not in crtl_lst:
                                # TODO
                                support_value = sdfs['SID'].nunique()
                                if support_value >= min_sup:
                                    supports = supports.append({'Items': repr(generated), 'Support': support_value},
                                                               ignore_index=True)
                                    three_dict[repr(item1)][repr(generated)] = sdfs
                                crtl_lst.add(repr(generated))
                        else:
                            for item, sdf in map(lambda x, y: (x, y), generated, sdfs):
                                if repr(item) not in crtl_lst:
                                    support_value = sdf['SID'].nunique()
                                    if support_value >= min_sup:
                                        supports = supports.append({'Items': repr(item), 'Support': support_value},
                                                                   ignore_index=True)
                                        three_dict[repr(item1)][repr(item)] = sdf
                                    crtl_lst.add(repr(item))
                    # event atom with sequence atom: PB with P->A should give PB->A
                    else:
                        generated, sdf = self.generate_for_unequal_len(item1, item2, branch, crtl_lst)
                        if repr(generated) not in crtl_lst:
                            support_value = sdf['SID'].nunique()
                            if support_value >= min_sup:
                                supports = supports.append({'Items': repr(generated), 'Support': support_value},
                                                           ignore_index=True)
                                three_dict[repr(item1)][repr(generated)] = sdf

                            crtl_lst.add(repr(generated))
        three_dict = {k: v for k, v in three_dict.items() if v}
        return supports, three_dict


    def spade(self, df: pd.DataFrame, min_sup: int):
        min_sup = min_sup * len(self._dataset)

        # (STEP 1): Find atoms and their support
        supports, F1 = self.find_F1(df, min_sup)
        # print(f"Step 1.:\n{supports}\n{F1}\n")
        # 2 Find frequent 2-sequences (containing 2 items) e.g. {AB}, {A}->{B}, {B}->{A}
        supports, item_tree = self.find_F2(F1, supports, min_sup)
        # print(f"Step 2.:\n{supports}\n{item_tree}\n")
        # 3 Find equivalence classes / sequences longer than 3 items
        # 4 Calculate support for sequences from step 3
        while item_tree:
            supports, item_tree = self.find_remaining(item_tree, supports, min_sup)
        return supports

#
# if __name__ == "__main__":
#     dataset = [
#             [['A', 'B'], ['C', 'D']],
#             [['A', 'U'], ['K', 'D'], ['B', 'B'], ['E', 'D']],
#             [['K', 'L', 'A']]
#         ]
#     spd = SPADE(dataset)
#     df = spd.read_dataset()
#     print(df)
#     support_results = spd.spade(df, 0.2)
#     print(support_results)
#     # support_results.to_csv(f'results_{datetime.now().strftime("%y-%m-%d-%H:%M")}.txt')