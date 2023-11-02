# Set variables
inputFilename = "output.txt"
mappingFilename = "mapping.txt"
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
        if (line.strip().startswith("Port") and begin == False):
            print("-- Beginning of interface output detected")
            begin = True
        # If we have already found the beginning of the output, it isn't a --More-- line, and it isn't the headers repeated again
        # Also ignore port-channels
        if (begin == True and not (("--More--") in line.strip()) and not line.strip().startswith("Po")):
            # Output from show int status is based on character count
            interface = line.strip()[0:9]
            description = line.strip()[10:28]
            status = line.strip()[29:41]
            vlan = line.strip()[42:53]
            # Debug Output
            if (debug == True):
                print(interface.strip() + "," + description.strip() + "," + status.strip() + "," + vlan.strip())