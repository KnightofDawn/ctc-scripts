Batch merge a folder of greyscale tiff color channel files into rgb images. Additionally: 

- Try to handle spelling errors. 
- If there's more than one tiff of a given color channel, create additional merges of all possible combinations of rgb channels.


----
# Dependencies
- Python 2.7 (if you need to install, [Anaconda](https://www.anaconda.com/download/) is recommended)
- [ImageMagick](https://www.imagemagick.org/script/index.php)

----
# Usage Notes

### Naming Conventions
Assumes the following file naming conventions: 
- `<id>-<channel_name>[-#].tif` 
- where `-#` is an optional number in the event of multiple same-channel images, e.g.,

```
    01-red.tif
    23-blue-2.tif   # an alternative blue channel scan of img 23
	14-green3.tif   # an alt green scan of img 14
```

Whitespace will be replaced with `-`. This *could* overwrite data if you had two files with identical names sans ` ` and `-`. 
e.g.,

	01 red 3.tif >> 01-red-3.tif
	01 red-3.tif >> 01-red-3.tif    # will clobber the file above

Trailing digits are interpreted alternative scan numbers and will be renamed
with a separating `-`. This, again, has clobber potential,
e.g.,

	01-red2.tif  >> 01-red-2.tif
	01-red 2.tif >> 01-red-2.tif    # will clobber the file above
	01 red 2.tif >> 01-red-2.tif    # will clobber the file above

### Spelling Errors
The first letter of a file's `channel_name` is taken to imply it's color.
e.g.,

	01-reed.tif        # red
	44-guleinoiena.tif # green
	10-b.tif           # blue
	10-bfue.tif        # excluded (see Brightfield Exclusion below)

### Brightfield Exclusion
Any .tif with a `channel_name` *starting with* `bf` is assumed to be a brightfield image and is excluded from any merges. So as long as blue channels are not named `bf*` things should be okay.
e.g.,

	01-bf.tif, 01-bflue.tif, 01-bf_actuallybluetrustme.tif # excluded
	01-bl.tif, 01-blbfue.tif  # blue
