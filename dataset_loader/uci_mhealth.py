#!/usr/bin/env python
# -*- coding: utf-8 -*-

# import pandas as pd
import numpy as np
import os
import csv
from collections import OrderedDict
from decimal import Decimal
from enum import Enum

import dataset_loader.sqlite_util as sqlite_util
from misc import mul_str_arr

DATA_PATH = "MHEALTHDATASET/MHEALTHDATASET"

DATASET_NAME = "uci_mhealth"

sampling_freq = Decimal('50.0')
sampling_interval = Decimal('1.0') / sampling_freq
# column_headings = [
#     "chest_acc_x",
#     "chest_acc_y",
#     "chest_acc_z",
#     "ecg_1",
#     "ecg_2",
#     "left_ankle_acc_x",
#     "left_ankle_acc_y",
#     "left_ankle_acc_z",
#     "left_ankle_gyro_x",
#     "left_ankle_gyro_y",
#     "left_ankle_gyro_z",
#     "left_ankle_magn_x",
#     "left_ankle_magn_y",
#     "left_ankle_magn_z",
#     "right_lower_arm_acc_x",
#     "right_lower_arm_acc_y",
#     "right_lower_arm_acc_z",
#     "right_lower_arm_gyro_x",
#     "right_lower_arm_gyro_y",
#     "right_lower_arm_gyro_z",
#     "right_lower_arm_magn_x",
#     "right_lower_arm_magn_y",
#     "right_lower_arm_magn_z",
#     "label",
# ]

samples_table = "__".join([DATASET_NAME, "samples"])
samples_schema = OrderedDict([
    ("sample_id"     , "INTEGER PRIMARY KEY"),
    ("timestamp"     , "DECIMAL"),
    ("subject_id"    , "INTEGER"),
    ("activity_id"   , "INTEGER"),
])
samples_n_columns = len(samples_schema)

sensor_readings_table = "__".join([DATASET_NAME, "sensor_readings"])
sensor_readings_schema = OrderedDict(
    [
        ("sample_id", "INTEGER PRIMARY KEY"),
    ] +
    [
        (k, "FLOAT") for k in
        mul_str_arr(["chest_acc"], ["x","y","z"]) +
        ["ecg_1", "ecg_2"] +
        mul_str_arr(["left_ankle", "right_lower_arm"],
                    ["acc", "gyro", "magn"],
                    ["x", "y", "z"])
    ] + 
    [("FOREIGN KEY", "(sample_id) REFERENCES {}(sample_id)".format(samples_table))]
)
sensor_readings_n_columns = len(sensor_readings_schema) - 1

def _load_dataset(path, loader):
    return OrderedDict(
        (int(filepath[15:-4]) , loader(os.path.join(path, DATA_PATH, filepath)))
        for filepath in os.listdir(os.path.join(path, DATA_PATH))
            if filepath.endswith('.log')
    )
    # insert timestamp and subject id
    # tbls_new = []
    # for subject in range(len(tbls)):
    #     nrows, ncols = np.shape(tbls[subject])
    #     timestamp = np.linspace(0.0, (nrows-1) * sampling_interval, nrows)
    #     tbl_new = np.full((nrows, ncols + 2), float(subject + 1))
    #     tbl_new[:, 0] = timestamp
    #     tbl_new[:, 1:-1] = tbls[subject]
    #     tbls_new.append(tbl_new)
    # return [ pd.DataFrame(t) for t in tbls_new ]

def load_dataset_to_mem(path):
    return _load_dataset(path, np.genfromtxt)

def _csv_loader(path):
    dtypes = [float] * 23 + [int]
    with open(path, 'r') as f:
        for row in csv.reader(f, delimiter='\t'):
            yield [ func(v) for (func, v) in zip(dtypes,row) ]

def load_dataset_to_sqlite(cur, path):
    tbls = _load_dataset(path, _csv_loader)
    store_dataset_to_sql(cur, tbls)

def row_generator(tbls, index=1):
    for (subject_id, tbl) in tbls.items():
        timestamp = Decimal('0')
        for row in tbl:
            yield (index, timestamp, subject_id, row)
            index = index + 1
            timestamp += sampling_interval

def samples_from_row(index, timestamp, subject_id, row):
    return (index, str(timestamp), subject_id, row[23])

def sensor_readings_from_row(index, timestamp, subject_id, row):
    return (index, *row[:-1])

def check_sqlite_table_not_exists(cur):
    return ((not sqlite_util.check_sql_table_exists(cur, samples_table)) and
           (not sqlite_util.check_sql_table_exists(cur, sensor_readings_table)))

def store_dataset_to_sql(cur, tbls):
    try:
        cur.execute("BEGIN TRANSACTION")
        sqlite_util.create_table_if_not_exists(cur, samples_table, samples_schema)
        sqlite_util.create_table_if_not_exists(cur, sensor_readings_table, sensor_readings_schema)
        _sql_stmt_samples = "INSERT INTO {} VALUES ({})".format(samples_table, ','.join(['?'] * samples_n_columns))
        _sql_stmt_sensors = "INSERT INTO {} VALUES ({})".format(sensor_readings_table, ','.join(['?'] * sensor_readings_n_columns))
        
        for row in row_generator(tbls):
            cur.execute(_sql_stmt_samples, samples_from_row(*row))
            cur.execute(_sql_stmt_sensors, sensor_readings_from_row(*row))
        cur.execute("COMMIT TRANSACTION")
    except:
        cur.execute("ROLLBACK TRANSACTION")

# def store_dataset_to_sql(cur, dfs):
#     sqlite_util.create_table_if_not_exists(cur, samples_table, samples_schema)
#     sqlite_util.create_table_if_not_exists(cur, sensor_readings_table, sensor_readings_schema)
#     cur.executemany("INSERT INTO {} VALUES ({})".format(samples_table, ','.join(['?'] * samples_n_columns)),
#         samples_row_generator(dfs))
#     cur.executemany("INSERT INTO {} VALUES ({})".format(sensor_readings_table, ','.join(['?'] * sensor_readings_n_columns)),
#         sensor_readings_row_generator(dfs))