def stripXML(filename):
	'''	A function that compresses SUMO queuing and tripinfo XML files using
	perl regular expressions by removing some redundant data

	Useage
	------
	stripXML(filename)
	stripXML('tripinfo.xml')

	Parameters
	----------
	filename : str
		The queuing or tripinfo file to be stripped

	author: Craig B. Rafter
	mailto: c.b.rafter@soton.ac.uk
	date: 01/09/2017
	copyright: GNU GPL v3.0 - attibute me if used
	'''
	import subprocess
	# Define regualr expressions
	regexList = [
	"s#.*<data timestep=.*\n.*<lanes/>\n.*</data>\n##g",
	's#queueing_length_experimental=".*"##g',
	"s#queueing_#q#g",
	"s#length#len#g",
	"s#timestep#tstep#g",
	"s#\n<!--([^\n]*\n+)+-->\n##g"]

	# Command to be piped to system perl 
	# -0777: "Slurp" the entire file according to `perldoc perlrun`
	# -p: continue through loop
	# -e: execute a one line command (as this is a command line perl call not a 
	#     call to a script)
	# -i: edit file inplace
	cmd = ['perl', '-0777', '-i', '-pe', 'regex', filename]
	# If queue file
	if('queue' in filename):
		for regexStr in regexList:
			cmd[4] = regexStr
			subprocess.call(cmd)
	# If tripfile
	else:
		cmd[4] = regexList[-1]
		subprocess.call(cmd)
