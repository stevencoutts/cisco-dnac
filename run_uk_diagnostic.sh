#!/bin/bash
# Script to run the UK diagnostic with credentials

# Use these credentials with the config.yaml server details
export DNAC_USERNAME="your-username-here"
export DNAC_PASSWORD="your-password-here"

# Run the diagnostic script
python scripts/get_uk_parent_id.py -d

# Check if we found a UK ID
echo ""
echo "===========================================" 
echo "Did we find a UK ID? If yes, let's try creating a building:"
echo "===========================================" 
echo ""
read -p "Enter building name (or press Enter to skip): " building_name

if [ ! -z "$building_name" ]; then
    python scripts/uk_building_direct.py -n "$building_name" -d
fi

echo ""
echo "===========================================" 
echo "Check the log files for detailed information:"
echo " - uk_parent_id.log"
echo " - uk_building_direct.log"
echo "===========================================" 