# Set variables
inputFilename = "vlan.txt"
needName = False
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
        #Need to fix this to detect VLANs without a name
        if line.strip().startswith("vlan"):
            print (line.split(" ")[1].strip() + ",", end="")
            needName = True
        elif line.strip().startswith("name") and needName is True:
            print (line.split(" ")[2].strip())
            needName = False
        elif needName is True:
            print ("")
            needName is False

