#!/usr/bin/env python
# -*- coding: utf-8 -*-
""" Batch merge single color channel tiffs into one file, ignoring bright field
images try to handle spelling errors. If there's more than one tiff of a given
color channel, create additional merges of all possible combinations of rgb
channels.

Assumes the following file naming conventions:
    <two digit id>-<channel_name><optional '-2/3/etc'>.tif
    e.g.,
        01-red.tif
        23-blue-2.tif    # an alternative blue channel scan of img 23
    
    Whitespace will be replaced with '-'. This *could* overwrite data if you
    had two files with identical names sans ' ' and '-'. 
    e.g., 
        01 red 3.tif >> 01-red-3.tif
        01 red-3.tif >> 01-red-3.tif    # will clobber the file above

Spelling Errors:
    The first letter of a file's channel_name is taken to imply it's color.
    e.g.,
        01-reed.tif        # red
        44-guleinoiena.tif # green
        10-b.tif           # blue
        10-bfue.tif        # excluded (see Brightfield Exclusion below)

Brightfield Exclusion: 
    Any .tif with a channel_name *starting with* 'bf' is assumed to be a bright
    field image and is excluded from any merges. So as long as blue channels
    are not named bf* things should be okay.
    e.g.,
        01-bf.tif, 01-bf-2.tif, 01-bf_actuallybluetrustme.tif # excluded
        01-bl.tif, 01-blbfue.tif                              # blue

Terminology (for variable names):
    chanel : one .tif file, red, green, blue, or bf (bright field)
        e.g., '01-red.tif'
    image : an area of the plate that is imaged, multiple channels correspond
        to one image. e.g., '01-*.tif'
    plate/sample : one sample of cells being imaged, a folder of images
"""

from __future__ import division
import numpy as np
import os
from glob import glob
import itertools
import argparse
import sys
import scipy.ndimage as ndi
import cv2
import imageio

### Script Info
__author__ = 'Nick Chahley, https://github.com/nickchahley'
__version__ = '0.2'
__day__ = '2018-06-17'

### Command line flags/options
def parse_args():
    parser = argparse.ArgumentParser()

    parser.add_argument('-d', '--defdir', type=str, help='Def dir for path dialog')
    parser.add_argument('-s', '--sigma', type=float, default=50., 
                        help='Sigma value for gaussian blur during illumination\
                        correction.')
    # possible future: preprocess on/off

    args = parser.parse_args()
    return args

### Options
opt = {}
opt['outdir'] = 'merged_corrected'

### Function Defs
def popup_message(text = '', title='Message'):
    try:
        # Python 3.x imports
        import tkinter as tk
        from tkinter import messagebox
    except ImportError:
        # Fall back to 2.x
        import Tkinter as tk
        import tkMessageBox as messagebox

    root = tk.Tk().withdraw()  # hide the root window

    messagebox.showinfo(title, text)  # show the messagebo
def path_dialog(whatyouwant):
    """ Prompt user to select a dir (def) or file, return its path

    In
    ---
    whatyouwant : str opts=['folder', 'file']

    Out
    ---
    path : str, Absolute path to file

    """
    import Tkinter
    # TODO allow multiple (shift-click) dir selections?
    root = Tkinter.Tk()
    root.withdraw()

    opt = {}
    opt['parent'] = root

    # opt['initialdir'] = './'
    opt['initialdir'] = args.defdir if args.defdir else './'


    if whatyouwant == 'folder':
        from tkFileDialog import askdirectory
        ask_fun = askdirectory
        # dirpath will be to dir that user IS IN when they click confirm
        opt['title'] = 'Select directory containing images to merge (be IN this folder)'

    if whatyouwant == 'file':
        from tkFileDialog import askopenfilename
        ask_fun = askopenfilename
        # opt['title'] = 'Select psd file to detect peaks from'
        # opt['filetypes'] = (('CSV files', '*.csv'), ('All files', '*.*'))

    path = ask_fun(**opt)

    # Quit if user doesn't select anything
    # No idea why an unset path is of type tuple
    if type(path) == tuple:
        m = 'No path selected, exiting'
        popup_message(m)
        sys.exit(m)

    return path
def format_trailing_nums(s):
    import re

    # trim .extension
    sp = '.'.join(s.split('.')[:-1])

    # match digits at end of string
    m = re.search('\d+$', sp)
    if not m:
        # string does not end in num
        new = s
    else:
        # string ends in num
        endnum = m.group()
        new = endnum.join(sp.split(endnum)[:-1])
        if new[-1] == '-':
            # Trailing '-', rm to avoid getting '01-blue--2.tif'
            new = new[:-1]
        ext = '.' + s.split('.')[-1]
        new = '-'.join((new, endnum)) + ext

    return new
def format_filenames(filenames):
    # replace whitespace
    filenames = [f.replace(' ', '-') for f in filenames]
    # ensure trailing digits are separated from channel_name w/ '-'
    filenames = [format_trailing_nums(f) for f in filenames]

    return filenames
def rename(filenames):
    for old, new in zip(filenames, format_filenames(filenames)):
        os.rename(old, new)
def tiffs_clean_filter(filenames):
    """ replace whitespace and exclude bright field tiff files
    """
    # rename_no_whitespace(filenames)
    rename(filenames)
    filenames = [f for f in filenames if '-bf' not in f]
    filenames.sort()
    return filenames
def tiffs_group(filenames):
    """ Group the channel files into dict by 2 digit prefix in filename.

    filenames : list
    ret channels : dict

    Naming conventions (assumed):
        <dd>-<color[text]>.tif : for 1st scans "norm"
        <dd>-<color[text]>-<d>.tif : for 2nd+ scans "abnorm"
    """
    nums = [f.split('-')[0] for f in filenames]
    nums = sorted(set(nums)) # rm repeats and back to sorted list
    
    ## Make dict of img num and channel files
    channels = [] 
    for n in nums:
        channels.append([f for f in filenames if n+'-' in f])
    channels.sort()
    channels = dict(zip(nums, channels))

    return channels
def channel_combos(files):
    """ Infer channel colors from names and return a dict with the names of all
    files for each color

    In
    ---
    files : list of strings

    Out
    ---
    combos : list of tuples, each tuple is one combo of rgb channels sorted
        in order of (r,g,b). Imagemagick will expect this order.
    """
    colors = {'r' : [],
              'g' : [],
              'b' : []}

    ## interrogate channel color from filename: look at first letter 
    ## and assume r* = red, etc
    for f in files:
        # get the first letter of word following '**-'
        c = f.split('-')[1].lower()[0]
        if c is 'r':
            colors['r'].append(f)
        elif c is 'g':
            colors['g'].append(f)
        elif c is 'b':
            colors['b'].append(f)

    # choose one item from each list, making all possible combos
    combos = [p for p in itertools.product(*colors.values())]

    # reverse alpha sort each tuple so that order is rgb -- imagemagick assumes
    # this order
    combos = [sorted(t, reverse=True) for t in combos]

    # List of tuples, each tuple is one combo of rgb channels
    return combos
def tiffs_iterate_combos(d):
    """ Ret dict with key for each image number make all possible rgb 
    combinations. 

    In
    ---
    d : dict of dicts of lists
        d = { <##> : { 
            r : [filenames], g : [], b : [] } 
            }

    Out
    ---
    imgs : dict of lists of tuples. Each tuple is one rgb combination. Each 
        list is all tuples for a given image number.
    """
    imgs = {}
    for k, v in d.iteritems():
        imgs[k] = channel_combos(v)
    
    # dict of list of tuples
    return imgs

def preproc_imgs(imgs, oudtdir='preproc'):
    """ Hastily commented preprocessing. 'uids' is a dumb name for this dict.

    imgs : dict w/ image numbers as keys 
    """
    # need to separate multi rgb comb images into unique im number
    uids = {}

    # Get a unique id for each distinct len3 list of r,g,b files
    for k, imls in imgs.iteritems():
        uids[k] = imls[0]
        if len(imls) > 1:
            # we have multiple rgb combos so append them image num/uid
            for i in range(1,len(imls)):
                uid = '-'.join((k, str(i+1)))
                uids[uid] = imls[i]
    
    def imread_as_8bit(imfile):
        """Open 16bit tiff and rescale to 8bit
        """
        im = cv2.imread(imfile, -1)
        im8 = cv2.convertScaleAbs(im, alpha = (255.0/65535.0))
        return im8
    def illum_correction(x, sigma, method='subtract'):
        """ Gaussian blurr background subtraction.
        Aim is to smooth image until it is devoid of features, but retains the
        weighted average intensity across the image that corresponds to the
        underlying illumination pattern. Then subtract

        This correction is only aware of the single image/channel that it is fed.
        It might be a better idea to try and implement illumination correction
        using multiple channels/images taken from the same experiment.
        """
        y = ndi.gaussian_filter(x, sigma=sigma, mode='constant', cval=0)
        if method == 'subtract':
            return cv2.subtract(x, y)
        elif method == 'divide':
            return cv2.divide(x, y)
        else:
            raise ValueError("Unsupported method: %s" %method)

    rgb = {}
    for uid, imls in uids.iteritems():
        # list uint8 array for one r, g, and b channel
        ims = [imread_as_8bit(f) for f in imls] 

        # Guassian blur bg subtraction for each channel
        ims = [illum_correction(x, args.sigma) for x in ims]

        rgb[uid] = np.dstack(ims)
    
    return rgb

def outfile_names(rgb, suffix='rgb', ext='.tif'):
    """ Take dict of num : rgb im and return outfilename : rgb num
    """

    for k in rgb.keys():
        ks = k.split('-')
        # if im num is of fmt '01-2' make name '01-suffix-2.ext'
        if len(ks) == 2:
            fname = '-'.join((ks[0], suffix, ks[-1])) + ext
        else:
            fname = '-'.join((k, suffix)) + ext
        rgb[fname] = rgb.pop(k)
    return rgb


### Main 
def main():
    path = path_dialog(whatyouwant = 'folder')
    os.chdir(path)
    filenames = glob("*.tif")
    filenames = tiffs_clean_filter(filenames)
    channels = tiffs_group(filenames)
    imgs = tiffs_iterate_combos(channels)
    rgb = preproc_imgs(imgs)
    rgb = outfile_names(rgb)

    # Make output dir if it does not exist
    if not os.path.exists(opt['outdir']):
        os.makedirs(opt['outdir'])
    
    for fname, im in rgb.iteritems():
        imageio.imwrite('/'.join((opt['outdir'], fname)), im)

    # FREEDOM


# run the main function
if __name__ == '__main__':
    args = parse_args()
    main()
    popup_message('Run complete')
