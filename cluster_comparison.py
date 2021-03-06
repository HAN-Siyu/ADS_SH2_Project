from sklearn.ensemble import RandomForestClassifier
import sklearn.model_selection
import pandas as pd
import sqlite3

from datetime import datetime as dt

from dataset_util import preprocess, uci_mhealth, uci_pamap2
from dataset_util.extract_input_features import all_feature, extract_features
# import matplotlib.pyplot as plt

import numpy as np
from config import SQLITE_DATABASE_FILE, TRAINING_SET_PROPORTION
# from scikitplot.metrics import plot_confusion_matrix, plot_roc
from evaluate_classification import evaluation_metrics
from cross_validation import cross_validate_multiclass_group_kfold
import os
from sklearn.decomposition import PCA
from sklearn.preprocessing import StandardScaler
from resample import resample

def centroid(pc, data):
    activities = [1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12]
    centroids = []
    for j in activities:
        f1 = []; f2 = []; f3 = []
        for i in range(len(data)):
            if data['activity_id'][i] == j:
                f1.append(pc[i, 0])
                f2.append(pc[i, 1])
                f3.append(pc[i, 2])
        centroids.append([np.median(f1), np.median(f2), np.median(f3)])


    return centroids

def euclidean(centroids, point):
    dist = 100000000
    for i in range(len(centroids)):
        if np.linalg.norm(centroids[i]-point) < dist:
            dist = np.linalg.norm(centroids[i]-point)
            label = str(i+1)

    return label

def activity_similarity(df, labels):
    activities_mhealth = [1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12]
    activities_pamap = [1, 2, 3, 4, 5, 6, 7, 9, 10, 11, 12, 13, 16, 17, 18, 19, 20, 24]
    df1 = pd.DataFrame()
    for i in activities_pamap:
        acc = [0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0]
        y=0
        for k in range(len(df)):
            if df['activity_id'][k] == i:
                y+=1
                acc[int(labels[k])-1] += 1
        for j in range(len(acc)):
            if y>0:
                acc[j] = (acc[j]/y)*100
        # acc = [(x/y)*100 for x in acc]
        df1[str(i)] = acc

    return df1

def deg2rad(data):
    for i in data.columns:
        if 'gyro' in i:
            temp = np.array(data[i].values)
            temp = [np.deg2rad(z) for z in temp]
            data[i] = temp

    return data

def drop_activities(acc, data):
    temp = []
    activities = data['activity_id'].values
    for i in data.index:
        if activities[i] in acc:
            temp.append(i)
    data = data.drop(temp, axis = 0)

    return data

def cv_main():
    bad_acc = [6.0, 7.0, 8.0, 12.0]
    pca = PCA(n_components=3)
    with sqlite3.connect(SQLITE_DATABASE_FILE) as conn:
        if os.path.exists('mhealth_features.pkl'):
            features_mhealth = pd.read_pickle('mhealth_features.pkl')
        else:
            data = pd.read_sql_query(uci_mhealth.raw_table_query_shared_data, conn)
            # data = drop_activities(bad_acc, data)
            data = resample(data, 100)
            data = deg2rad(data)
            # data = data.drop(['timestamp'], axis = 1)
            sliding_windows_mhealth = preprocess.full_df_to_sliding_windows(data)
            # sliding_windows_mhealth = uci_mhealth.to_sliding_windows_shared_data(conn)
            features_mhealth = extract_features(sliding_windows_mhealth, all_feature)
            features_mhealth.to_pickle('mhealth_features.pkl')
        if os.path.exists('pamap_features.pkl'):
            features_pamap = pd.read_pickle('pamap_features.pkl')
        else:
            data = pd.read_sql_query(uci_pamap2.raw_table_query_shared_data, conn)
            # data = resample(data, 50)
            data = data.drop(['timestamp'], axis = 1)
            sliding_windows_pamap = preprocess.full_df_to_sliding_windows(data)
            # sliding_windows_pamap = uci_pamap2.to_sliding_windows_shared_data(conn)
            features_pamap = extract_features(sliding_windows_pamap, all_feature)
            features_pamap.to_pickle('pamap_features.pkl')
    # features_mhealth = extract_features(sliding_windows_mhealth, all_feature)
    # features_mhealth.to_pickle('mhealth_features.pkl')
    x = StandardScaler().fit_transform(features_mhealth)
    pc_mhealth = (pca.fit_transform(x))
    x = StandardScaler().fit_transform(features_pamap)
    pc_pamap = (pca.fit_transform(x))

    [c1, c2, c3, c4, c5, c6, c7, c8, c9, c10, c11, c12] = centroid(pc_mhealth, features_mhealth)

    pamap_labels = []
    for i in range(len(features_pamap)):
        label = euclidean([c1, c2, c3, c4, c5, c6, c7, c8, c9, c10, c11, c12], pc_pamap[i, :])
        pamap_labels.append(label)
        # print(pc_pamap[i, :])
        # break

    features_pamap['mhealth labels'] = pamap_labels
    features_pamap.to_pickle('pamap_features.pkl')

    df = activity_similarity(features_pamap, pamap_labels)
    print(df)
    df.to_pickle('pamap_mhealth_mapping.pkl')
if __name__ == "__main__":
    # main()
    cv_main()
