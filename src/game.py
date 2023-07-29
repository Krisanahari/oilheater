import random

import comms
from object_types import ObjectTypes

import random
import comms
from object_types import ObjectTypes
from math import atan2, degrees, sqrt, pi, cos, sin
import sys


class Game:
    """
    Stores all information about the game and manages the communication cycle.
    Available attributes after initialization will be:
    - tank_id: your tank id
    - objects: a dict of all objects on the map like {object-id: object-dict}.
    - width: the width of the map as a floating point number.
    - height: the height of the map as a floating point number.
    - current_turn_message: a copy of the message received this turn. It will be updated everytime `read_next_turn_data`
        is called and will be available to be used in `respond_to_turn` if needed.
    """
    def __init__(self):

        self.last = None
        tank_id_message: dict = comms.read_message()
        self.tank_id = tank_id_message["message"]["your-tank-id"]
        self.enemy_id = tank_id_message["message"]["enemy-tank-id"]

        self.current_turn_message = None

        # We will store all game objects here
        self.objects = {}

        next_init_message = comms.read_message()
        while next_init_message != comms.END_INIT_SIGNAL:
            # At this stage, there won't be any "events" in the message. So we only care about the object_info.
            object_info: dict = next_init_message["message"]["updated_objects"]

            # Store them in the objects dict
            self.objects.update(object_info)

            # Read the next message
            next_init_message = comms.read_message()

        # We are outside the loop, which means we must've received the END_INIT signal

        # Let's figure out the map size based on the given boundaries

        # Read all the objects and find the boundary objects
        boundaries = []
        for game_object in self.objects.values():
            if game_object["type"] == ObjectTypes.BOUNDARY.value:
                boundaries.append(game_object)

        # The biggest X and the biggest Y among all Xs and Ys of boundaries must be the top right corner of the map.

        # Let's find them. This might seem complicated, but you will learn about its details in the tech workshop.
        biggest_x, biggest_y = [
            max([max(map(lambda single_position: single_position[i], boundary["position"])) for boundary in boundaries])
            for i in range(2)
        ]

        self.width = biggest_x
        self.height = biggest_y

    def read_next_turn_data(self):
        """
        It's our turn! Read what the game has sent us and update the game info.
        :returns True if the game continues, False if the end game signal is received and the bot should be terminated
        """
        # Read and save the message
        self.current_turn_message = comms.read_message()

        if self.current_turn_message == comms.END_SIGNAL:
            return False

        # Delete the objects that have been deleted
        # NOTE: You might want to do some additional logic here. For example check if a powerup you were moving towards
        # is already deleted, etc.
        for deleted_object_id in self.current_turn_message["message"]["deleted_objects"]:
            try:
                del self.objects[deleted_object_id]
            except KeyError:
                pass

        # Update your records of the new and updated objects in the game
        # NOTE: you might want to do some additional logic here. For example check if a new bullet has been shot or a
        # new powerup is now spawned, etc.
        self.objects.update(self.current_turn_message["message"]["updated_objects"])

        return True

    # def respond_to_turn(self):
    #     """
    #     This is where you should write your bot code to process the data and respond to the game.
    #     """

    #     # Write your code here... For demonstration, this bot just shoots randomly every turn.

    #     comms.post_message({
    #         "shoot": 90,
    #         "move":100,
    #         "path":[100, 100]
    #     })
#####################################################################################################################################################################################################
    def distance(self, x1, y1, x2, y2):
        return ((x2 - x1) ** 2 + (y2 - y1) ** 2) ** 0.5

    # Helper function to calculate the angle between two points in degrees
    def angle_between_points(self, x1, y1, x2, y2):
        return atan2(y2- y1, x2-x1) * 180/ pi

    # Helper function to get the tank's state
    def get_tank_state(self):
        tank = self.objects.get(self.tank_id)
        if tank:
            return tank["position"][0], tank["position"][1], tank["hp"], tank["powerups"]
        return None

    # Helper function to get the closest powerup's state
    def get_closest_powerup(self, tank_x, tank_y):
        closest_powerup = None
        closest_distance = float("inf")

        for obj_id, obj_info in self.objects.items():
            if obj_info["type"] == ObjectTypes.POWERUP.value:
                powerup_x, powerup_y = obj_info["position"]
                powerup_distance = self.distance(tank_x, tank_y, powerup_x, powerup_y)

                if powerup_distance < closest_distance:
                    closest_powerup = obj_info
                    closest_distance = powerup_distance

        return closest_powerup

    # Helper function to check if a tank can shoot at a target
    def can_shoot_target(self, tank_x, tank_y, target_x, target_y):
        target_distance = self.distance(tank_x, tank_y, target_x, target_y)
        if target_distance <= 700:  # Adjust this threshold based on the tank's shooting range
            return True
        return False
    
    def get_closest_boundary(self, tank_x, tank_y):
        # closest_boundary = None
        # closest_distance = float("inf")


        self.cl_boundaries = []
        for game_object in self.objects.values():
            if game_object["type"] == ObjectTypes.CLOSING_BOUNDARY.value:
                self.cl_boundaries.append(game_object)

        # Extract all X and Y values of the boundaries
        x_values = [boundary["position"][0] for boundary in self.cl_boundaries] #top left
        y_values = [boundary["position"][1] for boundary in self.cl_boundaries] #bottom left 
        z_values = [boundary["position"][2] for boundary in self.cl_boundaries] #bottom right
        a_values = [boundary["position"][3] for boundary in self.cl_boundaries] #top right

        print(x_values, file=sys.stderr)
        print(y_values, file=sys.stderr)
        print(z_values, file=sys.stderr)
        
        curr_coordinates = [tank_x, tank_y]
    
        if(abs(x_values[0][1] - tank_y) < 100):
            curr_coordinates[1] -= 50
        if(abs(y_values[0][0] - tank_x) < 100):
            curr_coordinates[0] += 50
        if(abs(z_values[0][1] - tank_y) < 100):
            curr_coordinates[1] += 50
        if(abs(a_values[0][0] - tank_x) < 100):
            curr_coordinates[0] -= 50
        
            
        
        # Find the x_value with the minimum difference from x1
        # min_difference_x = float('inf')
        # closest_x = None

        # for x_value in x_values:
        #     difference_x = abs(x_value - tank_x)
        #     if difference_x < min_difference_x:
        #         min_difference_x = difference_x
        #         closest_x = x_value

        # # Find the y_value with the minimum difference from y1
        # min_difference_y = float('inf')
        # closest_y = None

        # for y_value in y_values:
        #     difference_y = abs(y_value - tank_y)
        #     if difference_y < min_difference_y:
        #         min_difference_y = difference_y
        #         closest_y = y_value

        # # Determine which value is closer, x or y, and find the corresponding coordinate
        # if min_difference_x < min_difference_y:
        #     index_x = x_values.index(closest_x)
        #     corresponding_coordinate = (closest_x, y_values[index_x])
        # else:
        #     index_y = y_values.index(closest_y)
        #     corresponding_coordinate = (x_values[index_y], closest_y)

        return curr_coordinates

        # self.distances = [self.distance(self.objects[self.tank_id]["position"], corner) for corner in 
        #                   self.cl_boundaries[0]["position"]]
        

            
    
    # The bot's main decision-making function
    def respond_to_turn(self):
        # Get the tank's state
        tank_state = self.get_tank_state()
        if not tank_state:
            return

        tank_x, tank_y, tank_hp, tank_powerups = tank_state

        # Calculate the angle towards the center of the map
        center_x, center_y = self.width / 2, self.height / 2
        angle_to_center = self.angle_between_points(tank_x, tank_y, center_x, center_y)


        # Get the opponent's state if available
        opponent_state = None
        for obj_id, obj_info in self.objects.items():
            if obj_info["type"] == ObjectTypes.TANK.value and obj_id != self.tank_id:
                opponent_state = obj_info["position"][0], obj_info["position"][1], obj_info["hp"], obj_info["powerups"]
                break

        # Get the closest powerup if available
        closest_powerup = self.get_closest_powerup(tank_x, tank_y)
        # bn = self.move_away_from_boundary()

        desired_distance = 700
        target_x, target_y = tank_x, tank_y

        closest_boundary = self.get_closest_boundary(tank_x, tank_y)
        # Decide the tank's action based on the situation
        tank_action = {}

        # elif closest_boundary:
        #     boundary_x = closest_boundary[0]
        #     boundary_y = closest_boundary[1]

        #     # if (boundary_x - tank_x < 100) or (boundary_y - tank_y < 100):
        #     # angle_away_from_boundary = self.angle_between_points(tank_x, tank_y, boundary_x, boundary_y) + 180
        #     tank_action["path"] = [boundary_x, boundary_y]
        
        if self.can_shoot_target(tank_x, tank_y, self.objects[self.enemy_id]["position"][0], self.objects[self.enemy_id]["position"][1]):
            # Calculate the angle towards the enemy tank
            angle_to_enemy = self.angle_between_points(tank_x, tank_y, self.objects[self.enemy_id]["position"][0], self.objects[self.enemy_id]["position"][1])

            # Calculate the angle away from the enemy tank (180 degrees opposite direction)
            angle_away_from_enemy = (angle_to_enemy + 180) % 360

            # Calculate the target position to maintain desired_distance from the enemy tank
            target_x = tank_x + desired_distance * cos(angle_away_from_enemy * pi / 180)
            target_y = tank_y + desired_distance * sin(angle_away_from_enemy * pi / 180)

            # Check if the target position is within the map boundaries
            target_x = max(min(target_x, closest_boundary[0] + 50), 0)
            target_y = max(min(target_y, closest_boundary[1] + 50), 0)

            # Move the player tank towards the target position
            tank_action["path"] = [target_x, target_y]
        
        # If an opponent is nearby, try to shoot at them
        if opponent_state and self.can_shoot_target(tank_x, tank_y, opponent_state[0], opponent_state[1]):
            angle_to_opponent = self.angle_between_points(tank_x, tank_y, opponent_state[0], opponent_state[1])
            tank_action["shoot"] = angle_to_opponent

        # # If no opponent nearby, move towards the closest powerup
        # elif closest_powerup:
        #     powerup_x, powerup_y = closest_powerup["position"]
        #     angle_to_powerup = self.angle_between_points(tank_x, tank_y, powerup_x, powerup_y)
        #     tank_action = {"path": [powerup_x, powerup_y]}

        # # If there's nothing special, move randomly
        # elif self.last == None or self.last != [opponent_state[0], opponent_state[1]]:
        #     tank_action = {"path": [opponent_state[0], opponent_state[1]]}
        #     self.last = [opponent_state[0], opponent_state[1]]




        # Send the tank's action to the game server

        comms.post_message(tank_action)

