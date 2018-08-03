// Messy macros used in cropping training images for ML

/*macro "Save As PNG CTC [f1]" {*/
	/*// Save png to subdir*/
	/*subdir = "ctc/"*/
	/*title = getTitle();*/
	/*path = getDirectory("image");*/
	/*outfile = path + subdir + substring(title, 0, lengthOf(title)-4) + "-ctc.png"*/
	/*saveAs("PNG", outfile);*/
/*}*/
macro "Save As PNG [f1]" {
	// Save png dialog
	saveAs("PNG");
}
/*macro "Save As PNG bg [f3]" {*/
	/*// Save png to subdir*/
	/*subdir = "bg/"*/
	/*title = getTitle();*/
	/*path = getDirectory("image");*/
	/*outfile = path + subdir + substring(title, 0, lengthOf(title)-4) + "-bg.png"*/
	/*saveAs("PNG", outfile);*/
/*}*/

/*macro "Save As PNG wbc [f5]" {*/
	/*// Save png to subdir*/
	/*subdir = "wbc/"*/
	/*title = getTitle();*/
	/*path = getDirectory("image");*/
	/*outfile = path + subdir + substring(title, 0, lengthOf(title)-4) + "-wbc.png"*/
	/*saveAs("PNG", outfile);*/
/*}*/
macro "Make Composite [f6]" {
	// keybinding
	run("Make Composite")
}
macro "Stack to RGB [f7]" {
	// keybinding
	run("Stack to RGB")
}
/*macro "Open next with CTC [f5]" {
	// Save png to subdir
	run("Open Next");
	title = getTitle();
	path = getDirectory("image");
	subdir = "ctc/"
	ctcfile = path + subdir + substring(title, 0, lengthOf(title)-4) + ".png"
	// open ctcfile
	// somehow reset open next so that next open is the next tif
}/*
