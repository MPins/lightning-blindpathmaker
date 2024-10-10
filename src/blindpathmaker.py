import sys 
import ijson
import re
import os
import datetime
import time
from collections import Counter

from state_machine import state_machine

# This is a list of nodes which channels are being explored
# As we want to create a tree representing the connections between nodes, we avoid a connection pointing
# back to an element of the tree. It will be considered as a ramification later on the tree. 
nodesOnRecursivePath = []

# Default vale to num of blinded hops
num_blinded_hops = 2

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

class Channel:
    def __init__(self,channel_id, capacity, node1_pub, node2_pub, node1_time_lock_delta,
                 node2_time_lock_delta, node1_fee_base_msat, node1_fee_rate_milli_msat,
                 node2_fee_base_msat, node2_fee_rate_milli_msat):
        self.channel_id = channel_id
        self.capacity = capacity
        self.node1_pub = node1_pub
        self.node2_pub = node2_pub
        self.node1_time_lock_delta = node1_time_lock_delta
        self.node2_time_lock_delta = node2_time_lock_delta
        self.node1_fee_base_msat = node1_fee_base_msat
        self.node1_fee_rate_milli_msat = node1_fee_rate_milli_msat
        self.node2_fee_base_msat = node2_fee_base_msat
        self.node2_fee_rate_milli_msat = node2_fee_rate_milli_msat

class TreeNode:
    def __init__(self, value, channel = ""):
        self.value = value
        self.children = []
        self.channels = []
        if channel != "":
            self.channels.append(channel)
        nodesOnRecursivePath.append(value)

    def add_child(self, child_node, channel):
        # Adiciona um nó filho à lista de filhos
        self.children.append(child_node)
        self.channels.append(channel)

    def remove_child(self, child_node):
        # Remove um nó filho da lista de filhos
        self.children = [child for child in self.children if child != child_node]

    def __repr__(self):
        return f"{self.value}"

def node_channels_peers(node_id: str, json_file: str):
    sm1 = state_machine()

    # Open the JSON file for reading
    # TODO An error occurred: maximum recursion depth exceeded
    with open(json_file, 'r', encoding='utf-8', errors='ignore') as file:
        try:
            parser = ijson.parse(file)  # Create an iterator for the JSON data
            for prefix, event, value in parser:
                # Process the JSON events as needed
                # Perform transitions
                # If the transition results in completed nodes or edges data
                # Takes the data to mount the output
                if sm1.event(event, prefix, value) is True:
                    if sm1.data['data_type'] == "edges":
                        channel = Channel(sm1.data['edges.item.channel_id'], sm1.data['edges.item.capacity'],
                                          sm1.data['edges.item.node1_pub'], sm1.data['edges.item.node2_pub'],
                                          sm1.data['edges.item.node1_policy.time_lock_delta'],sm1.data['edges.item.node2_policy.time_lock_delta'],
                                          sm1.data['edges.item.node1_policy.fee_base_msat'], sm1.data['edges.item.node1_policy.fee_rate_milli_msat'],
                                          sm1.data['edges.item.node2_policy.fee_base_msat'], sm1.data['edges.item.node2_policy.fee_rate_milli_msat']
                                          )
                        if channel not in node_id.channels:
                            if sm1.data['edges.item.node1_pub'] == node_id.value and sm1.data['edges.item.node2_pub'] not in nodesOnRecursivePath and len(nodesOnRecursivePath) <= num_blinded_hops:
                                child = TreeNode(sm1.data['edges.item.node2_pub'], channel)
                                node_id.add_child(child, channel)
                                node_channels_peers(child, json_file)
                            elif sm1.data['edges.item.node2_pub'] == node_id.value and sm1.data['edges.item.node1_pub'] not in nodesOnRecursivePath and len(nodesOnRecursivePath) <= num_blinded_hops:
                                child = TreeNode(sm1.data['edges.item.node1_pub'], channel)
                                node_id.add_child(child, channel)
                                node_channels_peers(child, json_file)
            # Exhausted the node_id connections it can be removed from the recursive list
            nodesOnRecursivePath.remove(node_id.value)
            return
                    
        except ijson.JSONError as e:
            print(f"Error parsing JSON: {e}")


def main(json_file, amount, dest):
    try:
        # Create an instance of the state machine
        sm = state_machine()
        min_real_blinded_hops = 3
        blinded_hops = []

        # Open the JSON file for reading
        with open(json_file, 'r', encoding='utf-8', errors='ignore') as file:
            try:
                parser = ijson.parse(file)  # Create an iterator for the JSON data
                for prefix, event, value in parser:
                    # Process the JSON events as needed
                    # Perform transitions
                    # If the transition results in completed nodes or edges data
                    # Takes the data to mount the output
                    if sm.event(event, prefix, value) is True:
                        if sm.data['data_type'] == "nodes":
                            if sm.data['nodes.item.pub_key'] == dest:
                                root = TreeNode(dest)
                                node_channels_peers(root, json_file)
                                break
                if 'root' not in locals():
                    print(f"Destination not found: {dest}")
            except ijson.JSONError as e:
                print(f"Error parsing JSON: {e}")
    except Exception as e:
        print(f"An error occurred: {e}")
                
if __name__ == "__main__":
    if len(sys.argv) < 4 or len(sys.argv) > 5:
        print("Usage: python blindpathmaker.py <graph json_file> <amount in satoshis> <destination nodeid> <num blinded hops>")
        print(" <num blinded hops> is optional, default is 2")
        sys.exit(1)
    json_file = sys.argv[1]
    amount = sys.argv[2]
    dest = sys.argv[3]
    if len(sys.argv) == 5:
        num_blinded_hops = sys.argv[4]

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

