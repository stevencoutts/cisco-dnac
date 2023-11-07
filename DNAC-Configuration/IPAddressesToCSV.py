# Set variables
inputFilename = "l3interfaces.txt"
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
        if line.strip().startswith("interface Vlan"):
            print ("Vlan" + line.split("Vlan")[1].strip() + ",", end="")
            needName = True
        elif line.strip().startswith("ip address"):
            ipandmask=(line.split("address")[1].strip())
            ip=(ipandmask.split(" ")[0])
            mask=(ipandmask.split(" ")[1])
            print (ip + "," + mask)



