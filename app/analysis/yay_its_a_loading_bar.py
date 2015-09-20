import sys
import colors

def progress_bar(done, total):

	if total == 0:
		return

	toolbar_width = 40
	sys.stdout.write("\b" * (toolbar_width+8)) # return to start of line, after '['

	sys.stdout.write("[")
	dashes = int(float(done)/total*toolbar_width)
	for i in xrange(dashes):
	    # update the bar
	    sys.stdout.write("-")

	num = str( ("%.1f") % (100 * float(done)/total))
	sys.stdout.write(" " * (toolbar_width-dashes + (4-len(num))) + "] " + num + "%")
	sys.stdout.flush()

	if num == '100.0':
		sys.stdout.write("\n")

	


