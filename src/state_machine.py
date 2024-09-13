# State machine class
# The describegraph json file is suposed to be big enought to read whole and then process it,
# so we use this state machine to read each line at a time.
class state_machine:
    def __init__(self):
        self.state = 'initial'

    def event(self, event, prefix, data):

        if self.state == 'initial' and event == 'start_map':
            # Transitioning from 'initial' to 'map_started'
            self.state = 'map_started'
            return False
        elif self.state == 'map_started' and event == 'map_key':
            # "Transitioning from 'map_started' to 'mapping'
            self.state = 'mapping'
            return False
        elif self.state == 'map_started' and event == 'end_map':
            # "Transitioning from 'map_started' to 'map_ended'
            self.state = 'map_ended'
            return False
        elif self.state == 'mapping' and event == 'start_map':
            # ("Transitioning from 'mapping' to 'map_started'
            self.state = 'map_started'
            return False
        elif self.state == 'mapping' and event == 'start_array':
            # Transitioning from 'mapping' to 'array_started'
            self.state = 'array_started'
            return False
        elif self.state == 'mapping' and event == 'null':
            # Transitioning from 'mapping' to 'mapped'
            self.state = 'mapped'
            # Add a new key-value pair to the data field
            self.data[prefix] = ""
            return False
        elif self.state == 'mapping' and event == 'number':
            # Transitioning from 'mapping' to 'mapped'
            self.state = 'mapped'
            # Add a new key-value pair to the data field
            self.data[prefix] = data
            return False
        elif self.state == 'mapping' and event == 'string':
            # Transitioning from 'mapping' to 'mapped'
            self.state = 'mapped'
            # Add a new key-value pair to the data field
            self.data[prefix] = data
            return False
        elif self.state == 'mapping' and event == 'boolean':
            # Transitioning from 'mapping' to 'mapped'
            self.state = 'mapped'
            # Add a new key-value pair to the data field
            self.data[prefix] = data
            return False
        elif self.state == 'array_started' and event == 'start_map':
            # Transitioning from 'array_started' to 'map_started'
            self.state = 'map_started'           
            pieces = prefix.split('.')
            # If the prefix field has 2 pieces (e.g. "nodes.item") we initate the data field with nodes or edges
            if len(pieces) == 2: self.data = {"data_type":pieces[0]}
            return False 
        elif self.state == 'array_started' and event == 'end_array':
            # Transitioning from 'array_started' to 'array_ended'
            self.state = 'array_ended'
            return False
        elif self.state == 'mapped' and event == 'map_key':
            # Transitioning from 'mapped' to 'mapping'
            self.state = 'mapping'
            return False
        elif self.state == 'mapped' and event == 'end_map':
            # Transitioning from 'mapped' to 'map_ended'
            self.state = 'map_ended'
            return False
        elif self.state == 'map_ended' and event == 'end_array':
            # Transitioning from 'map_ended' to 'array_ended'
            self.state = 'array_ended'
            return False
        elif self.state == 'map_ended' and event == 'start_map':
            # Transitioning from 'map_ended' to 'map_started'
            self.state = 'map_started'
            pieces = prefix.split('.')
            # If the prefix field has 2 pieces (e.g. "nodes.item") we initate the data field
            if len(pieces) == 2: self.data = {"data_type":pieces[0]}            
            return False
        elif self.state == 'map_ended' and event == 'map_key':
            # Transitioning from 'map_ended' to 'mapping'
            self.state = 'mapping'
            return False
        elif self.state == 'map_ended' and event == 'end_map':
            # Transitioning from 'map_ended' to 'map_ended'
            self.state = 'map_ended'
            pieces = prefix.split('.')
            # If the prefix field has 2 pieces (e.g. "nodes.item") we return true.
            # This way the calling function know that the data field must be used 
            # imeddiatelly, because he might be initialised during the forward interactions
            if len(pieces) == 2: return True
        elif self.state == 'array_ended' and event == 'map_key':
            # Transitioning from 'array_ended' to 'mapping'
            self.state = 'mapping'
            return False
        elif self.state == 'array_ended' and event == 'end_map':
            # Transitioning from 'array_ended' to 'final'
            self.state = 'final'
            return False
        else:
            print("Invalid transition")
