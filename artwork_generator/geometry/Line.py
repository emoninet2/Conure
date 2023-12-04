import math
import numpy as np
from .Point import Point

class Line:
    def __init__(self, point1, point2):
        self.point1 = point1
        self.point2 = point2

    def __str__(self):
        return f"Line({self.point1}, {self.point2})"

    def length(self):
        return self.point1.distance(self.point2)

    def slope(self):
        if self.point2.x - self.point1.x == 0:
            return float('inf')  # Handle vertical lines with infinite slope
        return (self.point2.y - self.point1.y) / (self.point2.x - self.point1.x)

    def midpoint(self):
        mid_x = (self.point1.x + self.point2.x) / 2
        mid_y = (self.point1.y + self.point2.y) / 2
        return Point(mid_x, mid_y)

    def is_parallel(self, other_line):
        return self.slope() == other_line.slope()

    def is_perpendicular(self, other_line):
        return self.slope() * other_line.slope() == -1

    def translate(self, dx, dy):
        self.point1.translate(dx, dy)
        self.point2.translate(dx, dy)
        self.point2.translate(dx, dy)

    def rotate_around(self, center, angle_deg ):
        # Convert the angle to radians
        theta = math.radians(angle_deg)

        # Translate the line so that the center is at the origin
        self.point1.translate(-center.x, -center.y)
        self.point2.translate(-center.x, -center.y)

        # Rotate the points around the origin
        new_x1 = self.point1.x * math.cos(theta) - self.point1.y * math.sin(theta)
        new_y1 = self.point1.x * math.sin(theta) + self.point1.y * math.cos(theta)
        new_x2 = self.point2.x * math.cos(theta) - self.point2.y * math.sin(theta)
        new_y2 = self.point2.x * math.sin(theta) + self.point2.y * math.cos(theta)

        # Update the points with the rotated coordinates
        self.point1.x = new_x1
        self.point1.y = new_y1
        self.point2.x = new_x2
        self.point2.y = new_y2

        # Translate the line back to its original position
        self.point1.translate(center.x, center.y)
        self.point2.translate(center.x, center.y)


    def generate_staircase_line(self, pixel_size):
        dx = self.point2.x - self.point1.x
        dy = self.point2.y - self.point1.y
        magnitude = max(abs(dx), abs(dy))
        num_pixels = max(int(np.ceil(magnitude / pixel_size)), 1)

        # Calculate the increments for x and y directions
        x_increment = dx / num_pixels
        y_increment = dy / num_pixels

        # Determine the number of decimal places based on pixel_size
        decimal_places = max(len(str(pixel_size).split('.')[-1]), 0)

        # Generate the staircase line
        staircase_line = []
        x, y = self.point1.x, self.point1.y
        staircase_line.append(Point(x, y))
        for _ in range(num_pixels):
            x += x_increment
            y += y_increment
            snapped_x = round(x / pixel_size) * pixel_size
            snapped_y = round(y / pixel_size) * pixel_size
            snapped_x = round(snapped_x, decimal_places)
            snapped_y = round(snapped_y, decimal_places)
            point = Point(snapped_x, snapped_y)

            # Check if the new point is collinear with the last two points
            if len(staircase_line) >= 2:
                last_point = staircase_line[-1]
                second_last_point = staircase_line[-2]
                if self.is_collinear(second_last_point, last_point, point):
                    # Replace the last point with the new point
                    staircase_line[-1] = point
                else:
                    staircase_line.append(point)
            else:
                staircase_line.append(point)

        return staircase_line

    @staticmethod
    def is_collinear(p1, p2, p3):
        # Check if the three points are collinear
        return (p2.y - p1.y) * (p3.x - p2.x) == (p3.y - p2.y) * (p2.x - p1.x)
    


    
