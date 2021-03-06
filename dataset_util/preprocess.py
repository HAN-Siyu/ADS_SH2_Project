#!/usr/bin/env python
# -*- coding: utf-8 -*-

import numpy as np
import pandas as pd

from misc import mul_str_arr

DEFAULT_WINDOW_SIZE = 100
DEFAULT_WINDOW_OVERLAP = 0

def query_to_sliding_windows(cur, *args, **kwargs):
    return to_sliding_windows_cursor(cur, list(map(lambda x: x[0], cur.description)), *args, **kwargs)

def to_sliding_windows_cursor(cur, col_headings=None, size=DEFAULT_WINDOW_SIZE, overlap=DEFAULT_WINDOW_OVERLAP):
    if size <= overlap:
        raise ValueError("size must be strictly greater than overlap")
    l_arr = 0
    arr = []
    while True:
        fetched = cur.fetchmany(size - l_arr)
        if (l_arr + len(fetched)) < size:
            return
        else:
            arr = arr + fetched
            _arr = np.vstack(arr)
            l_arr = overlap
            arr = arr[size-overlap:]
            yield pd.DataFrame(_arr, columns=col_headings)
    return

# returns X, y, subject_id
def to_classification(df):
    return df.iloc[:,2:], df.iloc[:,0], df.iloc[:,1]

def full_df_to_sliding_windows(df, **kwargs):
    subject_ids = np.unique(df.loc[:,"subject_id"])
    for sid in subject_ids:
        df_subject = df.loc[df["subject_id"] == sid]
        yield to_sliding_windows(df_subject.values, col_headings=df.columns, **kwargs)

def to_sliding_windows(rows, col_headings=None, size=DEFAULT_WINDOW_SIZE, overlap=DEFAULT_WINDOW_OVERLAP):
    if size <= overlap:
        raise ValueError("size must be strictly greater than overlap")
    count = 0
    arr = []
    for row in rows:
        arr.append(row)
        count += 1
        if count >= size:
            _arr = np.vstack(arr)
            count = overlap
            arr = arr[size-overlap:]
            yield pd.DataFrame(_arr, columns=col_headings)
    return

# remaps column with label "activity_id" based on label_map, strip rows with activity_id == 0
# if strip_null_activity is True (default True).
def remap_label(df, label_map, strip_null_activity=True):
    df["activity_id"] = df["activity_id"].apply(lambda d: label_map.get(d, 0))
    if strip_null_activity:
        df = df[df["activity_id"] != 0]
    return df

def strip_null_activity(df, null_activity_id=0):
    return df[df["activity_id"] != null_activity_id]

def remap_subject_ids(dfs, sid_label='subject_id'):
    unik_sids = [ np.unique(df[sid_label]) for df in dfs ]
    n_sids = sum([ len(a) for a in unik_sids])
    new_ids = iter(range(1, n_sids+1))
    mappings = [ { old_id: next(new_ids) for old_id in sids } for sids in unik_sids ]
    for (df, mapping) in zip(dfs, mappings):
        df.loc[:, sid_label] = np.apply_along_axis(lambda x: np.array([mapping[v] for v in x]), 0, df.loc[:, sid_label])
    return dfs

def concat_datasets(*dfs, columns=None):
    if len(dfs) < 1:
        raise ValueError("no dataframe to concatenate")
    if len(dfs) == 1:
        return dfs[0]
    if columns is None:
        columns = dfs[0].columns
    new_val = np.vstack(map(lambda x: x.values, dfs))
    return pd.DataFrame(new_val, columns=columns)

def compute_triaxial_norm(df, remove_triaxial_vectors=True):
    columns = df.columns
    sensors = [ x[:-2] for x in columns if ('_x' in x) and ((x[:-2] + '_y') in columns) and ((x[:-2] + '_z') in columns) ]
    for sens in sensors:
        cols = df.loc[:, ["{}_x".format(sens), "{}_y".format(sens), "{}_z".format(sens)]].values
        norms = np.linalg.norm(cols, axis=1)
        if remove_triaxial_vectors:
            df.drop(labels=mul_str_arr([sens], ["x","y","z"]), axis=1, inplace=True)
        df.insert(loc=len(df.columns), column="{}_magnitude".format(sens), value=norms)
    return df

def test():
    x = [(1,"2",3.0), (4,"5",6.0),(7,"8",9.0)]
    slided = list(to_sliding_windows(x, col_headings=None, size=2))
    assert len(slided) == 1
    assert slided[0].equals(pd.DataFrame([[1,"2",3.0], [4,"5",6.0]]))
    
if __name__ == "__main__":
    test()

        
            
            