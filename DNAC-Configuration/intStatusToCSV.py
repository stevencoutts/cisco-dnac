# Set variables
inputFilename = "output.txt"
mappingFilename = "mapping.txt"
begin = False
debug = True
mapping = False
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
        if line.strip().startswith("Port") and begin is False:
            print("-- Beginning of interface output detected")
            print("--")
            begin = True
        # If we have already found the beginning of the output, it isn't a --More-- line
        # and it isn't the headers repeated again, also ignore port-channels
        if begin is True and "--More--" not in line.strip() and not line.strip().startswith("Po"):
            # Output from show int status is based on character count, I hope this always the same
            # Count not always the same :) Need to ditch this script and use running-config instead, bodge for now
            interface = line.strip()[0:9]
            description = line.strip()[10:31]
            status = line.strip()[32:43]
            vlan = line.strip()[43:55]
            # Debug Output
            if debug is True:
                print(interface.strip() + "," + description.strip() + "," + status.strip() + "," + vlan.strip())
            if mapping is True:
                with open(mappingFilename) as m:
                    # Loop
                    while True:
                        # Read line
                        mline = m.readline()
                        # End of file reached
                        if not mline:
                            break
                        # if the mapping line is for this vlan
                        if vlan.strip() in mline.split(",")[0]:
                            # Debug
                            if debug is True:
                                print(mline.strip())
                            print("--")
