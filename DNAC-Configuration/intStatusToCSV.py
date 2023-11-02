# Set variables
inputFilename = "output.txt"
begin = False
# Open file
with open(inputFilename) as f:
    # Loop
    while True:
        # Read line
        line = f.readline()
        # End of file reached
        if not line:
            break
        # Look for line before interface output begins, it should start with the word Port
        # If it is that line, set begin variable to True
        # We should only detect this once, the other times we can ignore
        if (line.strip().startswith("Port") and begin == False):
            print("-- Beginning of interface output detected")
            begin = True
        # If we have already found the beginning of the output, it isn't a --More-- line, and it isn't the headers repeated again
        if (begin == True and not (("--More--") in line.strip()) and not line.strip().startswith("Port")):
            print(line.strip())