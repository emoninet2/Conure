import math

class Point:
    """
    Represents a point in 2D space.

    Attributes:
        x (float): The x-coordinate of the point.
        y (float): The y-coordinate of the point.
    """

    def __init__(self, x=0, y=0):
        """
        Initializes a Point object with optional x and y coordinates.

        Args:
            x (float, optional): The x-coordinate of the point. Defaults to 0.
            y (float, optional): The y-coordinate of the point. Defaults to 0.
        """
        self.x = x
        self.y = y

    def __str__(self):
        """
        Returns a string representation of the Point object.

        Returns:
            str: A string representation of the point in the format "(x, y)".
        """
        return f"({self.x}, {self.y})"

    def __repr__(self):
        """
        Returns a string representation that can be used to recreate the Point object.

        Returns:
            str: A string representation of the point in the format "Point(x, y)".
        """
        return f"Point({self.x}, {self.y})"

    def __eq__(self, other):
        """
        Checks if the Point object is equal to another Point object.

        Args:
            other (Point): Another Point object to compare.

        Returns:
            bool: True if the points are equal, False otherwise.
        """
        if isinstance(other, Point):
            return self.x == other.x and self.y == other.y
        return False

    def __add__(self, other):
        """
        Adds two Point objects together.

        Args:
            other (Point): Another Point object to add.

        Returns:
            Point: A new Point object with the sum of their respective x and y coordinates.

        Raises:
            TypeError: If the other parameter is not a Point object.
        """
        if isinstance(other, Point):
            return Point(self.x + other.x, self.y + other.y)
        raise TypeError("Unsupported operand type: Point and {}".format(type(other)))

    def distance(self, other):
        """
        Calculates the Euclidean distance between the Point object and another Point object.

        Args:
            other (Point): Another Point object to calculate the distance to.

        Returns:
            float: The Euclidean distance between the two points.

        Raises:
            TypeError: If the other parameter is not a Point object.
        """
        if isinstance(other, Point):
            return ((self.x - other.x) ** 2 + (self.y - other.y) ** 2) ** 0.5
        raise TypeError("Unsupported operand type: Point and {}".format(type(other)))

    def rotate_around(self, center, angle_deg):
        """
        Rotates the Point object around a center point by a given angle in degrees.

        Args:
            center (Point): The center point to rotate around.
            angle_deg (float): The angle of rotation in degrees.

        Raises:
            TypeError: If the center parameter is not a Point object.
        """
        angle_rad = math.radians(angle_deg)
        if isinstance(center, Point):
            translated_x = self.x - center.x
            translated_y = self.y - center.y

            self.x = translated_x * math.cos(angle_rad) - translated_y * math.sin(angle_rad) + center.x
            self.y = translated_x * math.sin(angle_rad) + translated_y * math.cos(angle_rad) + center.y
        else:
            raise TypeError("Center parameter must be of type Point")

    def translate(self, dx, dy):
        """
        Translates the Point object by adding dx and dy values to its x and y coordinates, respectively.

        Args:
            dx (float): The translation value for the x-coordinate.
            dy (float): The translation value for the y-coordinate.
        """
        self.x += dx
        self.y += dy

    def normalize(self):
        """
        Normalizes the line by scaling its vector to have a length of 1.
        Returns a new Point representing the normalized line vector.

        The normalization process involves dividing the x and y coordinates of
        the line vector by its length.

        Returns:
            Point: A new Point representing the normalized line vector.
        """
        length = self.distance(Point(0, 0))
        if length == 0:
            return Point(0, 0)
        return Point(self.x / length, self.y / length)



    def snap_to_grid(self, grid_size):
        """
        Snaps the Point object to a grid by rounding its x and y coordinates to the nearest multiple of grid_size.

        Args:
            grid_size (float): The size of the grid.
        """
        self.x = round(self.x / grid_size) * grid_size
        self.y = round(self.y / grid_size) * grid_size

        decimal_points = len(str(grid_size).split('.')[1])

        self.x = round(self.x, decimal_points)
        self.y = round(self.y, decimal_points)

    def polar2cart(self, rho, angle):
        # Stores in cartesian coordinate a polar input where angles are in radians.
        self.x = rho * math.cos(angle)
        self.y = rho * math.sin(angle)
        # print((self.x,self.y))
        # print(rho,angle)

    def cart2polar(self,origin):
        # Returns the polar coordinates of the stored cartesian for a given origin.
        x0 = origin.x
        y0 = origin.y
        rho = math.sqrt((self.x-x0)**2+(self.y-y0)**2)
        angle = math.atan2((self.y-y0),(self.x-x0))
        # deg_angle = math.degrees(angle)

        return [rho,angle]
    def translatePolar(self, trans_angle):
        # Translates the point in polar coordinates a given angle trans_angle in degrees.
        rot = math.radians(trans_angle)
        [rho,angle] = self.cart2polar()
        new_angle = angle+rot
        self.polar(rho,new_angle)