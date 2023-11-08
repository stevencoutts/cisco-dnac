# Set variables
inputFilename = "routes.txt"
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
        if line.strip().startswith("ip route"):
            print (line.split("Vlan")[1].strip())
            needName = True



