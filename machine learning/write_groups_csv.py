#!/usr/bin/env python3
"""
From list of input images, output two csv files (train.csv/test.csv) that
contain the the group and path of each images. For each group, randomly split
the files between train/test 80:20. 

Group id is taken from the parent directory of the image file, ex:
    some/path/Group A/im.png  # Group A
    other/path/Group A/im.png # Group A
    some/path/Group B/im.png  # Group B
"""

import os
from glob import glob
import argparse
import pandas as pd
import numpy as np

def parse_args():
    ap = argparse.ArgumentParser()
    ap.add_argument('infiles', nargs='+', 
                    help='Image files, structured as <group>/image.ext')
    ap.add_argument('-d', '--dir', type=str, default='',
                    help='Output dir. Default names will be [train/test].csv')
    args = ap.parse_args()
    return args

def assign_integer_encoding(df, label_colname, integer_colname = 'integer_code'):
    """
    Add a column of labels encoded as integers
    """
    import sklearn.preprocessing
    df2 = df.copy()
    labels = df2[label_colname]

    label_encoder = sklearn.preprocessing.LabelEncoder()
    integer_encoded = label_encoder.fit_transform(np.array(labels))

    df2[integer_colname] = integer_encoded
    return df2

def main(infiles, outdir='', columns=['label', 'file_abspath']):
    absfiles = [os.path.abspath(f) for f in infiles]
    tupes = [(f.split('/')[-2], f) for f in absfiles]
    df = pd.DataFrame(tupes, columns=columns)

    def split_df_rand(df, porportion=0.8):
        """
        Ret ab : tuple of the split df a is of size porportion, b of
            1-porportion
        """
        msk = np.random.rand(len(df)) < 0.8
        a = df[msk]
        b = df[~msk]
        return (a, b)
    
    # Split df into two random samples (80/20) with porportional groups for
    # training/testing
    groups = np.unique(df[columns[0]])
    dfdict = {'train' : [], 'test' : []}
    for g in groups:
        gf = df[df[columns[0]] == g]
        gfs = split_df_rand(gf, 0.8)
        dfdict['train'].append(gfs[0])
        dfdict['test'].append(gfs[1])
    train = pd.concat(dfdict['train'])
    test = pd.concat(dfdict['test'])

    # assign integer encoding for simpler one-hot encoding downstream
    train = assign_integer_encoding(train, 'label')
    test = assign_integer_encoding(test, 'label')

    train.to_csv(os.path.join(outdir, 'train.csv'), index=False)
    test.to_csv(os.path.join(outdir, 'test.csv'), index=False)

    print('training set: %d files across %d labels' 
          %(len(train), len(np.unique(train[columns[0]]))))
    print('test set: %d files across %d labels' 
          %(len(test), len(np.unique(test[columns[0]]))))

if __name__ == '__main__':
    args = parse_args()
    main(args.infiles, args.dir)
