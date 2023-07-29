import random

import comms
from object_types import ObjectTypes

import random
import comms
from object_types import ObjectTypes
from math import atan2, degrees, sqrt, pi
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
        if target_distance <= 300:  # Adjust this threshold based on the tank's shooting range
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
        
        curr_coordinates = [tank_x, tank_y]
    
        if(abs(x_values[0][1] - tank_y) < 100):
            curr_coordinates[1] -= 25
            return curr_coordinates, True
        if(abs(y_values[0][0] - tank_x) < 100):
            curr_coordinates[0] += 25
            return curr_coordinates, True
        if(abs(z_values[0][1] - tank_y) < 100):
            curr_coordinates[1] += 25
            return curr_coordinates, True
        if(abs(a_values[0][0] - tank_x) < 100):
            curr_coordinates[0] -= 25
            return curr_coordinates, True
        return curr_coordinates, False        
    
    # Helper function to get the closest destructible wall in the positive x direction
    def get_closest_destructible_wall_in_pos_x(self, tank_x, tank_y):
        closest_wall_pos_x = None
        closest_wall_neg_x = None
        closest_distance_pos_x = float("inf")
        closest_distance_neg_x = float("inf")

        for game_object in self.objects.values():
            if game_object["type"] == ObjectTypes.DESTRUCTIBLE_WALL.value:
                wall_x, wall_y = game_object["position"]
                wall_distance = self.distance(tank_x, tank_y, wall_x, wall_y)

                # Check in the positive x direction
                if wall_x > tank_x and wall_distance < closest_distance_pos_x:
                    closest_wall_pos_x = game_object
                    closest_distance_pos_x = wall_distance

                # Check in the negative x direction
                if wall_x < tank_x and wall_distance < closest_distance_neg_x:
                    closest_wall_neg_x = game_object
                    closest_distance_neg_x = wall_distance

        if closest_distance_neg_x == closest_distance_pos_x:
            return True
        return False
    
        # Helper function to get the closest incoming bullet to the tank's position
    # def get_closest_incoming_bullet(self, tank_x, tank_y):
    #     closest_bullet = None
    #     closest_distance = float("inf")

    #     for game_object in self.objects.values():
    #         if game_object["type"] == ObjectTypes.BULLET.value:
    #             bullet_x, bullet_y = game_object["position"]
    #             bullet_velocity_x, bullet_velocity_y = game_object["velocity"]

    #             # Calculate the distance of the bullet's projected path from the tank's position
    #             bullet_distance = self.distance(tank_x, tank_y, bullet_x + bullet_velocity_x, bullet_y + bullet_velocity_y)

    #             if bullet_distance < closest_distance:
    #                 closest_bullet = game_object
    #                 closest_distance = bullet_distance

    #     return closest_bullet

        # Helper function to get the closest incoming bullet to the tank's position
    def get_closest_incoming_bullet(self, tank_x, tank_y):
        closest_bullet = None
        closest_distance = float("inf")

        for game_object in self.objects.values():
            if game_object["type"] == ObjectTypes.BULLET.value and game_object["tank_id"] == self.enemy_id:
                bullet_x, bullet_y = game_object["position"]
                bullet_velocity_x, bullet_velocity_y = game_object["velocity"]

                # Calculate the distance of the bullet's projected path from the tank's position
                bullet_distance = self.distance(tank_x, tank_y, bullet_x + bullet_velocity_x, bullet_y + bullet_velocity_y)

                # Perform LOS check to see if any walls intersect the line segment between tank and predicted bullet position
                los_clear = True
                for wall_obj in self.objects.values():
                    if wall_obj["type"] in [ObjectTypes.WALL.value, ObjectTypes.DESTRUCTIBLE_WALL.value]:
                        wall_x, wall_y = wall_obj["position"]
                        if self.intersects_wall(tank_x, tank_y, bullet_x + bullet_velocity_x, bullet_y + bullet_velocity_y, wall_x, wall_y):
                            los_clear = False
                            return closest_bullet, los_clear
                            break

                if bullet_distance < closest_distance and los_clear:
                    closest_bullet = game_object
                    closest_distance = bullet_distance

        return closest_bullet, True

    # Helper function to check if the line segment between two points intersects a wall
    def intersects_wall(self, x1, y1, x2, y2, wall_x, wall_y):
        # Calculate the distance from the wall to the line using the cross product
        return abs((x2 - x1) * (wall_y - y1) - (y2 - y1) * (wall_x - x1)) < 9  # Wall thickness is 18, use 9 as a buffer

    # def is_path_clear(self, start_x, start_y, target_x, target_y):
    #     # Bresenham's line algorithm to check for obstructions in the line of sight
    #     dx = abs(target_x - start_x)
    #     dy = abs(target_y - start_y)
    #     sx = -1 if start_x > target_x else 1
    #     sy = -1 if start_y > target_y else 1
    #     err = dx - dy

    #     while start_x != target_x or start_y != target_y:
    #         if start_x != target_x and start_y != target_y:
    #             if self.is_obstacle_at(start_x, start_y):
    #                 return False
    #         e2 = 2 * err
    #         if e2 > -dy:
    #             err -= dy
    #             start_x += sx
    #         if e2 < dx:
    #             err += dx
    #             start_y += sy

    #     return True

    # def is_obstacle_at(self, x, y):
    #     # Implement a function to check if there's an obstacle (wall) at the given coordinates (x, y)
    #     # You can use the wall positions to check for obstacles
    #     for game_object in self.objects.values():
    #         if game_object["type"] in [ObjectTypes.WALL.value, ObjectTypes.DESTRUCTIBLE_WALL.value]:
    #             wall_x, wall_y = game_object["position"]
    #             if wall_x == x and wall_y == y:
    #                 return True
    #     return False
        
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

        wall = self.get_closest_destructible_wall_in_pos_x(tank_x, tank_y)
        bullet, wall_condition = self.get_closest_incoming_bullet(tank_x, tank_y)
        # bullet = self.is_path_clear(tank_x, tank_y, opponent_state[0], opponent_state[1])
        closest_boundary, condition = self.get_closest_boundary(tank_x, tank_y)
        # Decide the tank's action based on the situation
        tank_action = {}


                    # If there's an incoming bullet, shoot back at it
        if bullet and wall_condition == True:
                bullet_x, bullet_y = bullet["position"]
                angle_to_bullet = self.angle_between_points(tank_x, tank_y, bullet_x, bullet_y)
                tank_action["shoot"] = angle_to_bullet
        
        if wall == True:
            tank_action = {"shoot": 90}

        # If an opponent is nearby, try to shoot at them
        if opponent_state and self.can_shoot_target(tank_x, tank_y, opponent_state[0], opponent_state[1]):
            angle_to_opponent = self.angle_between_points(tank_x, tank_y, opponent_state[0], opponent_state[1])
            tank_action["shoot"] = angle_to_opponent

        if closest_boundary and condition == True:
            boundary_x = closest_boundary[0]
            boundary_y = closest_boundary[1]

            # if (boundary_x - tank_x < 100) or (boundary_y - tank_y < 100):
            # angle_away_from_boundary = self.angle_between_points(tank_x, tank_y, boundary_x, boundary_y) + 180
            tank_action ["path"] = boundary_x, boundary_y

        # If no opponent nearby, move towards the closest powerup
        elif closest_powerup:
            powerup_x, powerup_y = closest_powerup["position"]
            angle_to_powerup = self.angle_between_points(tank_x, tank_y, powerup_x, powerup_y)
            tank_action ["path"] = powerup_x, powerup_y

        # If there's nothing special, move randomly
        elif self.last == None or self.last != [opponent_state[0], opponent_state[1]]:
            tank_action ["path"] = [opponent_state[0], opponent_state[1]]
            self.last = [opponent_state[0], opponent_state[1]]




        # Send the tank's action to the game server

        comms.post_message(tank_action)

