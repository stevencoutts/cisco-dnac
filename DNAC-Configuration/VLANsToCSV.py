# Set variables
inputFilename = "vlan.txt"
begin = False
debug = True
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
        if line.strip().startswith("vlan"):
            print (line.split(" ")[1].strip() + ",", end="")
        if line.strip().startswith("name"):
            print (line.split(" ")[2].strip())

