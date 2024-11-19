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
regularPaths = []
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

class RegularPath:
    def __init__ (self):
        self.node_id = []
        self.channel_id = []
        
    def add_hop(self, node_id, channel_id):
        self.node_id.insert(0, node_id)
        self.channel_id.insert(0, channel_id)

# Clone the path until the recursive depth   
def clone_regular_path(fromPath: RegularPath, toPath: RegularPath):
    # Cloning the path discarting the last hop, as we are inserting a hop at the same level 
    # of the last level.
    toPath.node_id = fromPath.node_id[1:]
    toPath.channel_id = fromPath.channel_id[1:]
class BlindedPath:
    def __init__ (self):
        self.node_id = []
        self.channel_id = []
        self.anonymity = 0
        self.feasability = 0
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

# Clone the path until the recursive depth   
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
    sm = state_machine()

    # Open the JSON file for reading
    with open(json_file, 'r', encoding='utf-8', errors='ignore') as file:
        try:
            parser = ijson.parse(file)  # Create an iterator for the JSON data
            path_is_used = False
            recursive_depth += 1
            for prefix, event, value in parser:
                # Process the JSON events as needed
                # Perform transitions
                # If the transition results in completed edges data
                # Takes the channel data to check if it is a insert on path or not
                if sm.event(event, prefix, value) is True:
                    if sm.data['data_type'] == "edges":
                        # If the channel is part of the current channel list already move to the next event                                      
                        if sm.data['edges.item.channel_id'] not in path.channel_id:
                            # Get the channel which current node is edge of it
                            if sm.data['edges.item.node1_pub'] == node_id:
                                # Skip if te depth was aleready reached
                                if recursive_depth <= num_blinded_hops:
                                    # If a path was already created on the current depth, create a new one
                                    if path_is_used is True:
                                        paths.append(BlindedPath())
                                        # If depth is greater than one, the new path should be a clone of the current one
                                        # where another branch is being created
                                        if recursive_depth > 1:
                                            clone_path(path, paths[len(paths)-1])
                                        # Create a leef on the current path
                                        paths[len(paths)-1].add_hop(sm.data['edges.item.node2_pub'],
                                                                sm.data['edges.item.channel_id'],
                                                                int(sm.data['edges.item.capacity']),
                                                                int(sm.data['edges.item.node2_policy.time_lock_delta']),
                                                                int(sm.data['edges.item.node2_policy.fee_base_msat']),
                                                                int(sm.data['edges.item.node2_policy.fee_rate_milli_msat']),
                                                                int(sm.data['edges.item.node2_policy.min_htlc']),
                                                                int(sm.data['edges.item.node2_policy.max_htlc_msat'])
                                                                )
                                        node_channels_peers(sm.data['edges.item.node2_pub'], paths[len(paths)-1], json_file)
                                    else:
                                        path_is_used = True
                                        path.add_hop(sm.data['edges.item.node2_pub'],
                                                    sm.data['edges.item.channel_id'],
                                                    int(sm.data['edges.item.capacity']),
                                                    int(sm.data['edges.item.node2_policy.time_lock_delta']),
                                                    int(sm.data['edges.item.node2_policy.fee_base_msat']),
                                                    int(sm.data['edges.item.node2_policy.fee_rate_milli_msat']),
                                                    int(sm.data['edges.item.node2_policy.min_htlc']),
                                                    int(sm.data['edges.item.node2_policy.max_htlc_msat'])                                                )
                                        node_channels_peers(sm.data['edges.item.node2_pub'], path, json_file)
                                else:
                                    break                                    
                            elif sm.data['edges.item.node2_pub'] == node_id:
                                if recursive_depth <= num_blinded_hops:
                                    if path_is_used is True:
                                        paths.append(BlindedPath())
                                        if recursive_depth > 1:
                                            clone_path(path, paths[len(paths)-1])
                                        paths[len(paths)-1].add_hop(sm.data['edges.item.node1_pub'],
                                                                sm.data['edges.item.channel_id'],
                                                                int(sm.data['edges.item.capacity']),
                                                                int(sm.data['edges.item.node1_policy.time_lock_delta']),
                                                                int(sm.data['edges.item.node1_policy.fee_base_msat']),
                                                                int(sm.data['edges.item.node1_policy.fee_rate_milli_msat']),
                                                                int(sm.data['edges.item.node1_policy.min_htlc']),
                                                                int(sm.data['edges.item.node1_policy.max_htlc_msat'])
                                                                )
                                        node_channels_peers(sm.data['edges.item.node1_pub'], paths[len(paths)-1], json_file)
                                    else:
                                        path_is_used = True
                                        path.add_hop(sm.data['edges.item.node1_pub'],
                                                    sm.data['edges.item.channel_id'],
                                                    int(sm.data['edges.item.capacity']),
                                                    int(sm.data['edges.item.node1_policy.time_lock_delta']),
                                                    int(sm.data['edges.item.node1_policy.fee_base_msat']),
                                                    int(sm.data['edges.item.node1_policy.fee_rate_milli_msat']),
                                                    int(sm.data['edges.item.node1_policy.min_htlc']),
                                                    int(sm.data['edges.item.node1_policy.max_htlc_msat'])
                                                    )
                                        node_channels_peers(sm.data['edges.item.node1_pub'], path, json_file)
                                else:    
                                    break                                    
            # Exhausted the node_id connections the depth can be decremented
            recursive_depth -= 1
            return
                    
        except ijson.JSONError as e:
            print(f"Error parsing JSON: {e}")

def anonymity(node_id, path: RegularPath, nodesAtPath, json_file: str):
    global recursive_depth, num_blinded_hops, regularPaths

    sm = state_machine()

    # Open the JSON file for reading
    with open(json_file, 'r', encoding='utf-8', errors='ignore') as file:
        try:
            parser = ijson.parse(file)  # Create an iterator for the JSON data
            path_is_used = False
            recursive_depth += 1
            for prefix, event, value in parser:
                # Process the JSON events as needed
                # Perform transitions
                # If the transition results in completed edges data
                # Takes the channel data to check if it is a insert on path or not
                if sm.event(event, prefix, value) is True:
                    if sm.data['data_type'] == "edges":
                        # If the channel is part of the current channel list already move to the next event                                      
                        if sm.data['edges.item.channel_id'] not in path.channel_id:
                            # Get the channel which current node is edge of it
                            if sm.data['edges.item.node1_pub'] == node_id:
                                # Skip if te depth was aleready reached
                                if recursive_depth <= num_blinded_hops:
                                    # If a path was already created on the current depth, create a new one
                                    if path_is_used is True:
                                        regularPaths.append(RegularPath())
                                        # If depth is greater than one, the new path should be a clone of the current one
                                        # where another branch is being created
                                        if recursive_depth > 1:
                                            clone_regular_path(path, regularPaths[len(regularPaths)-1])
                                        # Create a leef on the current path
                                        regularPaths[len(paths)-1].add_hop(sm.data['edges.item.node2_pub'],sm.data['edges.item.channel_id'])
                                        anonymity(sm.data['edges.item.node2_pub'], regularPaths[len(regularPaths)-1], nodesAtPath, json_file)
                                    else:
                                        path_is_used = True
                                        path.add_hop(sm.data['edges.item.node2_pub'], sm.data['edges.item.channel_id'])                                                
                                        anonymity(sm.data['edges.item.node2_pub'], path, nodesAtPath, json_file)
                                    if(sm.data['edges.item.node2_pub'] not in nodesAtPath):
                                        nodesAtPath.append(sm.data['edges.item.node2_pub'])
                                else:
                                    break                                    
                            elif sm.data['edges.item.node2_pub'] == node_id:
                                if recursive_depth <= num_blinded_hops:
                                    if path_is_used is True:
                                        regularPaths.append(RegularPath())
                                        if recursive_depth > 1:
                                            clone_regular_path(path, regularPaths[len(regularPaths)-1])
                                        regularPaths[len(regularPaths)-1].add_hop(sm.data['edges.item.node1_pub'], sm.data['edges.item.channel_id'])
                                        anonymity(sm.data['edges.item.node1_pub'], regularPaths[len(regularPaths)-1], nodesAtPath, json_file)
                                    else:
                                        path_is_used = True
                                        path.add_hop(sm.data['edges.item.node1_pub'],sm.data['edges.item.channel_id'])
                                        anonymity(sm.data['edges.item.node1_pub'], path, nodesAtPath, json_file)
                                    if(sm.data['edges.item.node2_pub'] not in nodesAtPath):
                                        nodesAtPath.append(sm.data['edges.item.node2_pub'])

                                else:    
                                    break                                    
            # Exhausted the node_id connections the depth can be decremented
            recursive_depth -= 1
            return
                    
        except ijson.JSONError as e:
            print(f"Error parsing JSON: {e}")

def main(json_file, amount, dest):
    global paths, regularPaths, recursive_depth
    try:
        # Create an instance of the state machine
        sm = state_machine()
        # Open the JSON file for reading
        count = 0
        with open(json_file, 'r', encoding='utf-8', errors='ignore') as file:
            try:
                parser = ijson.parse(file)  # Create an iterator for the JSON data
                for prefix, event, value in parser:
                    # Process the JSON events as needed
                    # Perform transitions
                    # If the transition results in completed nodes or edges data
                    # Takes the data to mount the output
                    if sm.event(event, prefix, value) is True:
                        count += 1
                        if sm.data['data_type'] == "nodes":
                            if sm.data['nodes.item.pub_key'] == dest:
                                print(f"\nDestination found: {dest}")
                                paths.append(BlindedPath())
                                node_channels_peers(dest, paths[len(paths)-1] , json_file)
                                dest_found = True
                                break
                    print(f"Nodes inspected: {count}", end="\r")
                if 'dest_found' not in locals():
                    print(f"Destination not found: {dest}")

            except ijson.JSONError as e:
                print(f"Error parsing JSON: {e}")

        # For the found blinded paths lets calculate the anonymity metric
        # This value represents the number of nodes that could feasibly be recipients for the blinded payment
        for path in paths:
            recursive_depth = 0
            nodesAtPath = []
            regularPaths.append(RegularPath())
            anonymity(path.node_id[0], regularPaths[len(regularPaths)-1], nodesAtPath, json_file)
            path.anonymity = len(nodesAtPath)
            path.feasability = path.max_capacity/int(amount)

        # For the found blinded paths lets create the output considering the amount restriction
        filename = "pathmaker.json"
        with open(filename, 'w', encoding='utf-8') as f_out:
            f_out.write("{\n\t\"Blinded Path Maker Version\": \"0.1.0\",\n")
            f_out.write("\t\"Blinded_Paths\": \n\t[\n")
            line = ""
            for path in paths:
                f_out.write(line)
                if (path.max_capacity > int (amount)):
                    f_out.write("\t\t{" + "\n" + "\t\t\t" + "\"Introduction_node\": \"" + str(path.node_id[0]) + "\",\n")
                    f_out.write("\t\t\t" + "\"Anonymity\": " + str(path.anonymity) + ",\n")
                    f_out.write("\t\t\t" + "\"Feasability\": " + str(path.feasability) + ",\n")
                    line = ("\t\t\t" + "\"Blinded_nodes\": [")
                    for node in path.node_id:
                        line += "\"" + str(node) + "\","
                    line = line[:-1] + "],\n"
                    f_out.write(line)
                    line = ("\t\t\t" + "\"Blinded_channels\": [")
                    for channel in path.channel_id:
                        line += "\"" + str(channel) + "\","
                    line = line[:-1] + "],\n"
                    f_out.write(line)
                    f_out.write("\t\t\t" + "\"Fee_base_msat\": " + str(path.total_fee_base_msat) + ",\n")
                    f_out.write("\t\t\t" + "\"Fee_rate_milli_msat\": " + str(path.total_fee_rate_milli_msat) + ",\n")
                    f_out.write("\t\t\t" + "\"Min_htlc\": " + str(path.path_min_htlc) + ",\n")
                    f_out.write("\t\t\t" + "\"Max_htlc_msat\": " + str(path.path_max_htlc) + ",\n")
                    f_out.write("\t\t\t" + "\"Time_lock_delta\": " + str(path.total_time_lock_delta) + "\n\t\t}")
                    line = ",\n"
            f_out.write("\n\t]\n}")
                

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

