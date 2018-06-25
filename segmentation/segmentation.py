#!/usr/bin/env python
# -*- coding: utf-8 -*-
# python 2.7
""" Rough implementation of fluro CTC image segmentation.

Goal: read and segment image, return an image mask containing the outlines of the segmented objects for user to open as a layer w/ original image.

Accepts 1+ images. Masks are written to a subdir 'masks' as PNGs.

This only works with single channel images, nogo on tri-channel merged images.
"""

from __future__ import division
import argparse
from scipy import ndimage
import numpy as np
import cv2
import mahotas as mh
import matplotlib.pyplot as plt # to save mask
import os
import scipy.ndimage as ndi

### Parse args

def parse_args():
    """ Functionalizing in a wacky attempt to be able to import functions
    from this file into a notebook or interactive session.
    """
    ap = argparse.ArgumentParser()
    ap.add_argument('image', nargs='+', # gather all cline args into a list
                    help='Path to input image(s)')
    ap.add_argument('-c', '--cliff', default=0, type=int,
                    help='Apply a crude cliff threshold highpass filter. \
                    Aimed at supressing filter pore signal (intensity in \
                    uint16)')
    args = ap.parse_args()
    return args

### Segmentation Group
def filter_cliff(img, thresh):
    """Crude cliff filter for supressing filter pores' signal.
    """
    img_t = img.copy()
    img_t[img_t < thresh] = 0
    return img_t
def th_rc(img, sigma=2.0):
    """ Riddler-Calvard thresholding w/ gaussian smooth. 
    ret bin_img
    """
    imgf = mh.gaussian_filter(img, float(sigma))
    T_rc = mh.rc(img)
    bin_img = imgf > T_rc
    return bin_img
def segment_objects(img, bin_img, sigma=2.0, show=False):
    """ Preform watershed witchcraft and rm bordering objects
    """
    imgf = mh.gaussian_filter(img.astype(float), sigma)
    maxima = mh.regmax(mh.stretch(imgf))
    maxima,_= mh.label(maxima)

    dist = mh.distance(bin_img)
    dist = 225 - mh.stretch(dist)
    watershed = mh.cwatershed(dist, maxima)
    watershed *= bin_img

    return watershed
def postprocessing(watershed, min_size = 5):
    """ Find and discard objects that we don't want.

    min_size : unknown if this is sane, needs work/testing/scope scale
    """
    # rm cells touching border
    cleaned = mh.labeled.remove_bordering(watershed)

    ## filter by size here
    # filtered = mh.labled.remove_regions_where(watershed, sizes < min_size)

    # relabel indecies
    cleaned, nr_objects = mh.labeled.relabel(cleaned)

    return cleaned
def segmentation(img, sigma=2.0, threshold_type='rc'):
    """ Really rough image segmentation (objects from bg). 

    threshold_type : 'yen' or 'rc', defaults to yen if not 'rc'
    Needs tests for circularity, refinement
    """
    if threshold_type == 'rc':
        # Riddler-Calvar is more conservative, more likely to include filter
        # pores as foreground.
        bin_img = th_rc(img, sigma=sigma)

    else:
        # Yen is more aggressive, more likely to exclude cells from foreground.
        # However, this fucks up mh.distance
        from skimage.filters.thresholding import threshold_yen
        img_smooth = ndi.filters.gaussian_filter(img, sigma=sigma)
        bin_img = threshold_yen(img_smooth)

    watershed = segment_objects(img, bin_img, sigma=sigma)
    watershed = postprocessing(watershed) # "cleaned watershed"

    return watershed
def segmentation_mask(img, outline=True):
    """ Return the segmented mask (bool) of an image. 
    Optionally as an outline only.
    """
    # separate objects from background 
    seg_img = segmentation(img, sigma=2.0)
    mask = seg_img < 1

    if outline == True:
        # edge detection
        edge_hrz = ndimage.sobel(mask, 0)
        edge_vrt = ndimage.sobel(mask, 1)
        magnitude = np.hypot(edge_hrz, edge_vrt)
        magnitude = magnitude.astype('bool') # from float16
        return magnitude

    else:
        return mask

def circularity(watershed):
    """Return dict of object/segment id and circularity value.

    watershed : ndarray of labeled objects where bg = 0 and fg > 1

    Depends on mahotas
    """
    ws = watershed
    d = {}

    for ob_id in np.unique(ws):
        if ob_id != 0:
            ob = ws == ob_id
            circ = mh.features.roundness(ob)
            d[ob_id] = circ

    return d

### In/Out
def output_mask(imagefile, mask, outdir='masks'):
    """ Write mask as a png in subdir "masks". Derive name from image filename.
    """
    base = os.path.basename(imagefile)
    maskfile = '.'.join(base.split('.')[:-1])
    maskfile = maskfile + '-mask.png'

    # append outdir to path/to/imagedir, add path to maskfile
    outdir = '/'.join((os.path.dirname(imagefile), outdir))
    maskfile = '/'.join((outdir, maskfile))

    # Make masks dir if DNE
    if not os.path.exists(outdir):
        os.makedirs(outdir)

    print('Writing mask to: %s' % maskfile)
    plt.imsave(maskfile, mask)

### Main etc
def single_image_run(imagefile):
    """pseudo-main
    """
    im = cv2.imread(imagefile, -1)
    if args.cliff > 0:
        print('Cliff filter passing intensity > %d' % args.cliff)
        im = filter_cliff(im, args.cliff)
    mask = segmentation_mask(im)
    
    # Convert mask into 3 color channel array, color the first channel
    tmp = np.dstack((mask, mask, mask))
    mask_color = np.zeros(tmp.shape)
    mask_color[mask] = [1, 0, 0]

    output_mask(imagefile, mask_color)
def main():
    """Iterate over multiple image files.
    """
    for i in args.image:
        # Exclude brightfield images
        if 'bf' not in os.path.basename(i):
            single_image_run(i)

### Run
if __name__ == "__main__":
    args = parse_args()
    main()
