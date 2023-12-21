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
            print (line.split(" ")[2].strip() + "," + line.split(" ")[3].strip() + "," + line.split(" ")[4].strip())
            needName = True



