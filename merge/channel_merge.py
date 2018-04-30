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

### Script Info
__author__ = 'Nick Chahley, https://github.com/nickchahley'
__version__ = '0.1.2'
__day__ = '2018-04-30'

import subprocess
import os
from glob import glob
import itertools
import argparse
import sys

### Command line flags/options
parser = argparse.ArgumentParser()
parser.add_argument('-v', '--debug', dest='debug', action='store_true')
parser.set_defaults(debug=False)
parser.add_argument('-d', '--defdir', type=str, help='Def dir for path dialog')
# Access an arg value by the syntax 'args.<argument_name>'
args = parser.parse_args()

### Options
opt = {}
opt['outdir'] = 'merged'

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
    if args.debug:
        print('sorted filenames bf excluded:')
        print(filenames)
    return filenames
def tiffs_group(filenames):
    """ Group the channel files into dict by 2 digit prefix in filename.

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
def im_command(rgb, outfile, outdir):
    """ Generate imagemagick command from tuple of rgb channel filenames.
    """   
    outfile = '%s/%s' %(outdir, outfile)
    cmd = 'convert %s -combine %s' %(' '.join(rgb), outfile)
    return cmd
def merge_im(imgs, outdir):
    """ Generate the imagemagick merge commands.

    imgs : dict 
    """
    # will be {outputname : tuple of r,g.b}
    outs = {}

    ## Generate output filenames
    for imgid, rgb_tuples in imgs.iteritems():
        for i in range(len(rgb_tuples)):
            outname = '%s-rgb-%d.tif' %(imgid, i+1)
            # don't append '-1' to first rgb combo outfile
            outname = outname.replace('-1.tif', '.tif')
            outs[outname] = rgb_tuples[i]

    cmds = [im_command(v, k, outdir) for k, v in outs.iteritems()]
    cmds.sort()

    return cmds
def merge_im_dbg(imgs, outdir):
    """ Generate the imagemagick merge commands.

    imgs : dict 
    """
    # will be {outputname : tuple of r,g.b}
    outs = {}

    ## Generate output filenames
    for imgid, rgb_tuples in imgs.iteritems():
        for i in range(len(rgb_tuples)):
            outname = '%s-rgb-%d.tif' %(imgid, i+1)
            # don't append '-1' to first rgb combo outfile
            outname = outname.replace('-1.tif', '.tif')
            outs[outname] = rgb_tuples[i]

    cmds = [im_command(v, k, outdir) for k, v in outs.iteritems()]
    cmds.sort()

    return cmds, outs

### Graveyard
def rename_no_whitespace(filenames):
    # Assume we are in dir containing files to be renamed
    for f in filenames:
        os.rename(f, f.replace(" ", "-"))

### Test
## testing scratch
def test():
    names = ['06-blue.tif', '06-blue2.tif', '06-blue-2.tif', '06-b7ue.tif',
             '06-blue10.tif', '07 red.tif', '07 red 2.tif', '07 red-3.tif']
    renames = rename(names)

    for n, r in zip(names, renames):
        if n is not r:
            print('%s >> %s' %(n, r))
        else:
            print(n)
# test()

### Main 
def main():
    path = path_dialog(whatyouwant = 'folder')
    os.chdir(path)
    filenames = glob("*.tif")
    filenames = tiffs_clean_filter(filenames)
    channels = tiffs_group(filenames)
    imgs = tiffs_iterate_combos(channels)

    # Make output dir if it does not exist
    if not os.path.exists(opt['outdir']):
        os.makedirs(opt['outdir'])

    cmds = merge_im(imgs, opt['outdir'])
    
    # Messed up by making the command a straight string, subprocess takes a
    # command as a list with each item being a whitespace separation
    for c in cmds:
        if args.debug:
            f = '/'.join((opt['outdir'], 'debug.log'))
            s = 'echo %s >> %s' %(c, f)
            os.system(s)
        c = c.split(' ')
        subprocess.call(c)
        print(c)

# run the main function
if __name__ == '__main__':
    main()
    popup_message('Run complete')
    # TODO if there was a debug flag we could
    # locals().update(main())
