import random

import comms
from object_types import ObjectTypes

import random
import comms
from object_types import ObjectTypes
from math import atan2, degrees, sqrt, pi


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
        # return 90 - (180 / 3.1415926535) * (3.1415926535 + 3.1415926535 - (3.1415926535 + atan2(y2 - y1, x2 - x1)))
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
        if target_distance <= 200:  # Adjust this threshold based on the tank's shooting range
            return True
        return False
    
    # def move_away_from_boundary(self):

    #     tank_state = self.objects[self.tank_id]
    #     tank_x, tank_y = tank_state["position"]

    #     nearest_boundary_distance = float("inf")
    #     nearest_boundary_position = None

    #     # Find the nearest boundary
    #     for obj_id, obj_state in self.objects.items():
    #         if obj_state["type"] == ObjectTypes.BOUNDARY.value:
    #             boundary_x, boundary_y = obj_state["position"]
    #             distance_to_boundary = self.distance(tank_x, tank_y, boundary_x, boundary_y)
    #             if distance_to_boundary < nearest_boundary_distance:
    #                 nearest_boundary_distance = distance_to_boundary
    #                 nearest_boundary_position = (boundary_x, boundary_y)

    #     if nearest_boundary_position is not None:
    #         return (-boundary_x, -boundary_y)


    # The bot's main decision-making function
    def respond_to_turn(self):
        # Get the tank's state
        tank_state = self.get_tank_state()
        if not tank_state:
            return

        tank_x, tank_y, tank_hp, tank_powerups = tank_state

        # bullets_to_avoid = []
        # for obj_id, obj_state in self.objects.items():
        #     if obj_state["type"] == ObjectTypes.BULLET.value:
        #         bullet_x, bullet_y = obj_state["position"]
        #         bullet_vx, bullet_vy = obj_state["velocity"]
        #         bullet_distance = self.distance(bullet_x, bullet_y, tank_x, tank_y)
        #         time_to_reach = bullet_distance / sqrt(bullet_vx ** 2 + bullet_vy ** 2)
        #         if time_to_reach <= 1.5:  # Adjust this threshold based on the bullet speed
        #             bullets_to_avoid.append((bullet_x, bullet_y))

        # Calculate the angle towards the center of the map
        center_x, center_y = self.width / 2, self.height / 2
        angle_to_center = self.angle_between_points(tank_x, tank_y, center_x, center_y)

        # Check if there are bullets on the way to the center
        # for bullet_x, bullet_y in bullets_to_avoid:
        #     angle_to_bullet = self.angle_between_points(tank_x, tank_y, bullet_x, bullet_y)
        #     angle_difference = abs(angle_to_bullet - angle_to_center)
        #     if angle_difference < 90:  # Adjust this angle threshold based on your strategy
        #         # If the bullet is on the way, calculate a new angle to avoid it
        #         angle_to_center += 90 if angle_to_bullet > angle_to_center else -90

        # Get the opponent's state if available
        opponent_state = None
        for obj_id, obj_info in self.objects.items():
            if obj_info["type"] == ObjectTypes.TANK.value and obj_id != self.tank_id:
                opponent_state = obj_info["position"][0], obj_info["position"][1], obj_info["hp"], obj_info["powerups"]
                break

        # Get the closest powerup if available
        closest_powerup = self.get_closest_powerup(tank_x, tank_y)
        # bn = self.move_away_from_boundary()

        # Decide the tank's action based on the situation
        tank_action = None

        # If an opponent is nearby, try to shoot at them
        if opponent_state and self.can_shoot_target(tank_x, tank_y, opponent_state[0], opponent_state[1]):
            angle_to_opponent = self.angle_between_points(tank_x, tank_y, opponent_state[0], opponent_state[1])
            tank_action = {"shoot": angle_to_opponent}

        # If no opponent nearby, move towards the closest powerup
        elif closest_powerup:
            powerup_x, powerup_y = closest_powerup["position"]
            angle_to_powerup = self.angle_between_points(tank_x, tank_y, powerup_x, powerup_y)
            tank_action = {"path": [powerup_x, powerup_y]}

        # If there's nothing special, move randomly
        elif self.last == None or self.last != [center_x, center_y]:
            tank_action = {"path": [center_x, center_y]}
            self.last = [center_x, center_y]

        # Send the tank's action to the game server



        comms.post_message(tank_action)

