import random
import numpy as np
import sys
import math

import comms
from object_types import ObjectTypes


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
        tank_id_message: dict = comms.read_message()
        self.tank_id = tank_id_message["message"]["your-tank-id"]
        self.enemy_tank_id = tank_id_message["message"]["enemy-tank-id"]

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

    def find_safest_point_away_from_boundary(self, player_x, player_y):
        # Get all the CLOSING_BOUNDARY objects
        closing_boundaries = [
            obj for obj in self.objects.values() if obj["type"] == ObjectTypes.CLOSING_BOUNDARY.value
        ]

        # Find the nearest closing boundary
        nearest_boundary = None
        min_distance = float("inf")

        boundary_x, boundary_y = closing_boundaries[0]["position"][0]  # Take the position of just one vertex (all 4 vertices are the same for a boundary)
        distance = math.sqrt((boundary_x - player_x) ** 2 + (boundary_y - player_y) ** 2)

        if distance < min_distance:
            min_distance = distance
            nearest_boundary = closing_boundaries[0]

        if nearest_boundary:
            # Calculate the direction of the closing boundary (using the velocity of one of the walls)
            boundary_velocity_x, boundary_velocity_y = nearest_boundary["velocity"][0]
            boundary_angle = math.degrees(math.atan2(boundary_velocity_y, boundary_velocity_x))
            boundary_angle %= 360  # Ensure the angle is between 0 and 360 degrees

            # Calculate the angle to run away from the boundary
            # We'll add 180 degrees to the boundary's angle to move in the opposite direction
            new_angle = (boundary_angle + 180) % 360

            # Calculate the destination point 100 units away from the player in the opposite direction of the boundary
            destination_x = player_x + 100.0 * np.cos(np.radians(new_angle))
            destination_y = player_y + 100.0 * np.sin(np.radians(new_angle))

            # Check if the destination point is inside a wall or outside the map boundaries
            # If it's not safe to move to the calculated destination, move randomly instead
            if self.is_safe_destination(destination_x, destination_y):
                return destination_x, destination_y

        # If no safe destination found or no closing boundary nearby, return None
        return None, None

    def is_safe_destination(self, x, y):
        # Check if the given point is inside a wall or outside the map boundaries
        # You need to implement this method based on the game's map information
        # It should return True if the point is safe to move to, and False otherwise.
        # For simplicity, you can assume that the player cannot move outside the map boundaries.

        # Implement your logic here based on the map information
        # For example, check if the point is inside a wall or outside the map boundaries
        # Return True if it's safe, False otherwise.
        # For simplicity, let's assume all points are safe for now.
        return True

    def respond_to_turn(self):
        """
        This is where you should write your bot code to process the data and respond to the game.
        """

        # Get the player's tank object based on its ID
        player_tank = self.objects.get(self.tank_id)

        if not player_tank:
            print("Player tank not found!")
            return

        # Calculate the position of the center of the player's tank
        player_x, player_y = player_tank["position"]

        # Find a safe destination point away from the closing boundary
        safe_destination_x, safe_destination_y = self.find_safest_point_away_from_boundary(player_x, player_y)

        if safe_destination_x is not None and safe_destination_y is not None:
            # If a safe destination is found, post the "path" message to move towards it
            comms.post_message({"path": [safe_destination_x, safe_destination_y]})
        else:
            # If no safe destination found or no closing boundary nearby, just shoot randomly
            comms.post_message({"shoot": random.uniform(0, random.randint(1, 360))})

        # self.movement()

    # def respond_to_turn(self):
    #     """
    #     This is where you should write your bot code to process the data and respond to the game.
    #     """

    #     # Write your code here... For demonstration, this bot just shoots randomly every turn.
    #     # comms.post_message({
    #     #     "shoot": random.uniform(0, random.randint(1, 360))
    #     # })
    #     # self.movement()
    
    def movement(self):
        """
        Zone avoidance with a 100.0 radius around the player.
        """

        # Get the position of the player
        player_position = self.objects[self.tank_id]["position"]

        print(self.objects[self.tank_id]["position"], file=sys.stderr)

        self.closing_boundaries = self.get_gameObject_by_type(ObjectTypes.CLOSING_BOUNDARY.value)

        print(self.closing_boundaries, file=sys.stderr)

        # Check if any of the closing boundaries intersect the 100.0 radius around the player
        boundary_position = self.closing_boundaries[0]["position"]
        for corner in boundary_position:
            # Calculate the distance between the player and the boundary corner
            distance = self.calculate_distance(player_position, corner)
            print(distance, file=sys.stderr)
            # If the distance is less than 100.0 (collision detected), move away from the boundary
            if distance < 665.0:
                # Calculate the direction to the nearest wall corner
                direction_to_nearest_wall = self.calculate_direction(player_position, corner)

                # Calculate the new position to move away from the wall by 100.0 units
                new_position = self.move_player(player_position, direction_to_nearest_wall, -100.0)

                # Update the player's position in the objects dictionary
                self.objects[self.tank_id]["position"] = new_position

                # Post the new position as the desired path
                comms.post_message({
                    "path": new_position
                })

                # Break the loop as we only need to avoid one boundary at a time
                break



    # def movement(self):
    #     """
    #     Default zone avoidance
    #     """

    #     self.middle = [self.width/2, self.height/2]

    #     print(self.objects[self.tank_id]["position"], file=sys.stderr)

    #     self.closing_boundaries = self.get_gameObject_by_type(ObjectTypes.CLOSING_BOUNDARY.value)

    #     print(self.closing_boundaries, file=sys.stderr)

    #     self.distances = [self.calculate_distance(self.objects[self.tank_id]["position"], corner) for corner in 
    #                       self.closing_boundaries[0]["position"]]
        
    #     print(self.distances, file=sys.stderr)

    #     if min(self.distances) - (self.objects[self.tank_id]["position"][0] + self.objects[self.tank_id]["position"][0]) < 100.0:
    #         nearest_corner = self.closing_boundaries[0]["position"][self.distances.index(min(self.distances))]
    #         direction_to_nearest_wall = self.calculate_direction(self.objects[self.tank_id]["position"], nearest_corner)

    #         new_position = self.move_player(self.objects[self.tank_id]["position"], direction_to_nearest_wall, -100.0)
    #         print("working", new_position, file=sys.stderr)
    #         comms.post_message({
    #             "path": new_position
    #         })

    # #     if ((self.closing_boundaries[0]["position"][3][1] - self.objects[self.tank_id]["position"][1]) < 100.0):
    # #         comms.post_message({
    # #             "path": [self.objects[self.tank_id]["position"][0], self.objects[self.tank_id]["position"][1] - 100.0]
    # #         })
    # #     if ((self.objects[self.tank_id]["position"][1]) - self.closing_boundaries[0]["position"][1][1] < 100.0):
    # #         comms.post_message({
    # #             "path": [self.objects[self.tank_id]["position"][0], self.objects[self.tank_id]["position"][1] + 100.0]
    # #         })

    def get_gameObject_by_type(self, type):
        gObject = []
        for game_object in self.objects.values():
            if game_object["type"] == type:
                gObject.append(game_object)
        return gObject

    def calculate_distance(self, point1, point2):
        x1, y1 = point1
        x2, y2 = point2
        distance = math.sqrt((x2 - x1) ** 2 + (y2 - y1) ** 2)
        return distance
    
    def calculate_direction(self, player_pos, nearest_corner):
        player_x, player_y = player_pos
        corner_x, corner_y = nearest_corner

        # Calculate the differences in x and y coordinates
        dx = corner_x - player_x
        dy = corner_y - player_y

        # Determine the direction based on the differences in coordinates
        if abs(dx) >= abs(dy):
            # The dominant direction is left or right
            if dx >= 0:
                direction_x, direction_y = 1, 0  # Right
            else:
                direction_x, direction_y = -1, 0  # Left
        else:
            # The dominant direction is top or bottom
            if dy >= 0:
                direction_x, direction_y = 0, 1  # Bottom
            else:
                direction_x, direction_y = 0, -1  # Top

        return [direction_x, direction_y]

    
    def move_player(self, player_pos, direction, distance):
        """
        Update the player's position based on the given direction and distance.
        """
        player_x, player_y = player_pos
        direction_x, direction_y = direction

        # Calculate the magnitude (length) of the direction vector
        magnitude = math.sqrt(direction_x ** 2 + direction_y ** 2)

        # Avoid division by zero, in case the direction vector is [0, 0]
        if magnitude == 0:
            return player_pos

        # Normalize the direction vector to have a length of 1
        normalized_direction_x = direction_x / magnitude
        normalized_direction_y = direction_y / magnitude

        # Calculate the new position by moving along the normalized direction vector by the specified distance
        new_x = player_x + normalized_direction_x * distance
        new_y = player_y + normalized_direction_y * distance

        return [new_x, new_y]
