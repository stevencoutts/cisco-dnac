# Set input file
inputFilename = "output.txt"
# Open file
with open(inputFilename) as f:
    # Loop
    while True:
        # Read line
        line = f.readline()
        # End of file reached
        if not line:
            break
        # Strip out --More- lines
        if not (("--More--") in line.strip()):
            print(line.strip())
