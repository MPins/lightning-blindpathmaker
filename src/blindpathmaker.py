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
recursive_depth = 0
paths = []

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

class BlindedPath:
    def __init__ (self):
        self.node_id = []
        self.channel_id = []
        self.capacity = []
        self.max_capacity = 0
        self.time_lock_delta = []
        self.total_time_lock_delta = 0
        self.fee_base_msat = []
        self.total_fee_base_msat = 0
        self.fee_rate_milli_msat = []
        self.total_fee_rate_milli_msat = 0
        self.min_htlc = []
        self.path_min_htlc = 0
        self.max_htlc = []
        self.path_max_htlc = 0
        
    def add_hop(self, node_id, channel_id, capacity: int, time_lock_delta: int, fee_base_msat: int, fee_rate_milli_msat: int,
                  min_htlc: int, max_htlc: int):
        self.node_id.insert(0, node_id)
        self.channel_id.insert(0, channel_id)
        self.capacity.insert(0, capacity)
        if capacity < self.max_capacity or self.max_capacity == 0:
            self.max_capacity = capacity
        self.time_lock_delta.insert(0, time_lock_delta)
        self.total_time_lock_delta += time_lock_delta
        self.fee_base_msat.insert(0, fee_base_msat)
        self.total_fee_base_msat += fee_base_msat
        self.fee_rate_milli_msat.insert(0, fee_rate_milli_msat)
        self.total_fee_rate_milli_msat += fee_rate_milli_msat
        self.min_htlc.insert(0, min_htlc)
        if min_htlc > self.path_min_htlc:
            self.path_min_htlc = min_htlc
        self.max_htlc.insert(0, max_htlc)
        if max_htlc < self.path_max_htlc or self.path_max_htlc == 0:
            self.path_max_htlc = max_htlc

# TODO clone the path until the recursive depth   
def clone_path(fromPath: BlindedPath, toPath: BlindedPath):
    # Cloning the path discarting the alst hop, as we are inserting a hop at the same level 
    # of the last level.
    toPath.node_id = fromPath.node_id[1:]
    toPath.channel_id = fromPath.channel_id[1:]
    for index in range(recursive_depth - 2, -1, -1):
        toPath.capacity.insert(0, fromPath.capacity[index])
        if fromPath.capacity[index] < toPath.max_capacity or toPath.max_capacity == 0:
            toPath.max_capacity = fromPath.capacity[index]
        toPath.time_lock_delta.insert(0, fromPath.time_lock_delta[index])
        toPath.total_time_lock_delta += fromPath.time_lock_delta[index]
        toPath.fee_base_msat.insert(0, fromPath.fee_base_msat[index])
        toPath.total_fee_base_msat += fromPath.fee_base_msat[index]
        toPath.fee_rate_milli_msat.insert(0, fromPath.fee_rate_milli_msat[index])
        toPath.total_fee_rate_milli_msat += fromPath.fee_rate_milli_msat[index]
        toPath.min_htlc.insert(0, fromPath.min_htlc[index])
        if fromPath.min_htlc[index] > toPath.path_min_htlc:
            toPath.path_min_htlc = fromPath.min_htlc[index]
        toPath.max_htlc.insert(0, fromPath.max_htlc[index])
        if fromPath.max_htlc[index] < toPath.path_max_htlc or toPath.path_max_htlc == 0:
            toPath.path_max_htlc = fromPath.max_htlc[index]

def node_channels_peers(node_id: str, path: BlindedPath, json_file: str):
    global recursive_depth, num_blinded_hops, paths
    sm1 = state_machine()

    # Open the JSON file for reading
    with open(json_file, 'r', encoding='utf-8', errors='ignore') as file:
        try:
            parser = ijson.parse(file)  # Create an iterator for the JSON data
            path_is_used = False
            recursive_depth += 1
            for prefix, event, value in parser:
                # Process the JSON events as needed
                # Perform transitions
                # If the transition results in completed nodes or edges data
                # Takes the data to mount the output
                if sm1.event(event, prefix, value) is True:
                    if sm1.data['data_type'] == "edges":                                      
                        if sm1.data['edges.item.channel_id'] not in path.channel_id:
                            if sm1.data['edges.item.node1_pub'] == node_id:
                                if recursive_depth <= num_blinded_hops:
                                    if path_is_used is True:
                                        paths.append(BlindedPath())
                                        if recursive_depth > 1:
                                            clone_path(path, paths[len(paths)-1])
                                        paths[len(paths)-1].add_hop(sm1.data['edges.item.node2_pub'],
                                                                sm1.data['edges.item.channel_id'],
                                                                int(sm1.data['edges.item.capacity']),
                                                                int(sm1.data['edges.item.node2_policy.time_lock_delta']),
                                                                int(sm1.data['edges.item.node2_policy.fee_base_msat']),
                                                                int(sm1.data['edges.item.node2_policy.fee_rate_milli_msat']),
                                                                int(sm1.data['edges.item.node2_policy.min_htlc']),
                                                                int(sm1.data['edges.item.node2_policy.max_htlc_msat'])
                                                                )
                                        node_channels_peers(sm1.data['edges.item.node2_pub'], paths[len(paths)-1], json_file)
                                    else:
                                        path_is_used = True
                                        path.add_hop(sm1.data['edges.item.node2_pub'],
                                                    sm1.data['edges.item.channel_id'],
                                                    int(sm1.data['edges.item.capacity']),
                                                    int(sm1.data['edges.item.node2_policy.time_lock_delta']),
                                                    int(sm1.data['edges.item.node2_policy.fee_base_msat']),
                                                    int(sm1.data['edges.item.node2_policy.fee_rate_milli_msat']),
                                                    int(sm1.data['edges.item.node2_policy.min_htlc']),
                                                    int(sm1.data['edges.item.node2_policy.max_htlc_msat'])                                                )
                                        node_channels_peers(sm1.data['edges.item.node2_pub'], path, json_file)
                                else:
                                    break                                    
                            elif sm1.data['edges.item.node2_pub'] == node_id:
                                if recursive_depth <= num_blinded_hops:
                                    if path_is_used is True:
                                        paths.append(BlindedPath())
                                        if recursive_depth > 1:
                                            clone_path(path, paths[len(paths)-1])
                                        paths[len(paths)-1].add_hop(sm1.data['edges.item.node1_pub'],
                                                                sm1.data['edges.item.channel_id'],
                                                                int(sm1.data['edges.item.capacity']),
                                                                int(sm1.data['edges.item.node1_policy.time_lock_delta']),
                                                                int(sm1.data['edges.item.node1_policy.fee_base_msat']),
                                                                int(sm1.data['edges.item.node1_policy.fee_rate_milli_msat']),
                                                                int(sm1.data['edges.item.node1_policy.min_htlc']),
                                                                int(sm1.data['edges.item.node1_policy.max_htlc_msat'])
                                                                )
                                        node_channels_peers(sm1.data['edges.item.node1_pub'], paths[len(paths)-1], json_file)
                                    else:
                                        path_is_used = True
                                        path.add_hop(sm1.data['edges.item.node1_pub'],
                                                    sm1.data['edges.item.channel_id'],
                                                    int(sm1.data['edges.item.capacity']),
                                                    int(sm1.data['edges.item.node1_policy.time_lock_delta']),
                                                    int(sm1.data['edges.item.node1_policy.fee_base_msat']),
                                                    int(sm1.data['edges.item.node1_policy.fee_rate_milli_msat']),
                                                    int(sm1.data['edges.item.node1_policy.min_htlc']),
                                                    int(sm1.data['edges.item.node1_policy.max_htlc_msat'])
                                                    )
                                        node_channels_peers(sm1.data['edges.item.node1_pub'], path, json_file)
                                else:    
                                    break                                    
            # Exhausted the node_id connections the depth can be decremented
            recursive_depth -= 1
            return
                    
        except ijson.JSONError as e:
            print(f"Error parsing JSON: {e}")


def main(json_file, amount, dest):
    global paths
    try:
        # Create an instance of the state machine
        sm = state_machine()
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
                                paths.append(BlindedPath())
                                node_channels_peers(dest, paths[len(paths)-1] , json_file)
                                dest_found = True
                                break
                if 'dest_found' not in locals():
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

