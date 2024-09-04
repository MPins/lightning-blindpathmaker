import sys 
import ijson
import re
import os
import datetime
import time
from collections import Counter

# This function receives input JSON file and create the new output JSON file 
# without the alias field.
# Sometimes the field ends on the next line with the comma (,)
# When it happens it will be deleted also
def remove_alias(input_file, output_file):
    with open(input_file, 'r', encoding='utf-8', errors='ignore') as f_in:
        with open(output_file, 'w', encoding='utf-8') as f_out:
            alias = False
            for line in f_in:
                if alias == True:
                    alias = False
                    if ',' in line:
                        continue
                if not re.search(r'"alias"', line):
                    f_out.write(line)
                else:
                    if ',' not in line:
                        alias = True

def main(json_file, amount, dest):
    print("Dummy")

if __name__ == "__main__":
    if len(sys.argv) != 4:
        print("Usage: python blindpathmaker.py <graph json_file> <amount in satoshis> <destination nodeid>")
        sys.exit(1)
    json_file = sys.argv[1]
    amount = sys.argv[2]
    dest = sys.argv[3]

    # create another file ignoring the alias field due the erros it cause when parsing it
    # because of unexpected characteres
    file_name, file_extension = os.path.splitext(json_file)

    s_json_file = file_name + "_s" + file_extension
    remove_alias(json_file, s_json_file)
        
    main(s_json_file, amount, dest)

    # delete the created file
    if os.path.exists(s_json_file):
        # Delete the file
        os.remove(s_json_file)

