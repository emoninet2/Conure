from .Point import Point
from .Polygon import Polygon
import copy
import math

class Octagon:
    def __init__(self, apothem_ref):
        self.apothem_ref = apothem_ref
        outer_radius = apothem_ref / math.cos(math.pi / 8)
        self.vertices = []
        self.ref_angle = []
        self.boundaries_enable = 1
        self.factors = [1] * 8
        self.stretch_factors = [1] * 4

        for i in range(8):
            x = outer_radius * math.cos(-math.pi / 8)
            y = outer_radius * math.sin(-math.pi / 8)
            p = Point(x, y)
            pOrigin = Point(0, 0)
            p.rotate_around(pOrigin, 45 * i)
            self.vertices.append(Point(p.x, p.y))
            self.ref_angle.append(math.pi / 4 * i)

    # ... all other methods stay unchanged ...

    def cardinal_symmetry(self, axis, points2mirror):
        if axis == 'NS':
            if points2mirror == 'E':
                idx_objective = 7
                for i in [-1, 0, 1, 2]:
                    idx_reference = i
                    idx_objective -= 1
                    idx_reference %= len(self.vertices)
                    idx_adjusted = idx_objective % len(self.vertices)
                    self.vertices[idx_adjusted].y = self.vertices[idx_reference].y
                    self.vertices[idx_adjusted].x = -self.vertices[idx_reference].x
            elif points2mirror == 'W':
                idx_reference = 7
                for i in [-1, 0, 1, 2]:
                    idx_reference -= 1
                    idx_objective = i
                    idx_reference %= len(self.vertices)
                    idx_adjusted = idx_objective % len(self.vertices)
                    self.vertices[idx_adjusted].y = self.vertices[idx_reference].y
                    self.vertices[idx_adjusted].x = -self.vertices[idx_reference].x
            else:
                print('ERROR: Wrong points2mirror argument. For NS symmetry axis, only western (W) or eastern (E) points can be mirrored.')

        elif axis == 'WE':
            if points2mirror == 'N':
                idx_reference = 0
                idx_objective = 1
                for i in range(4):
                    idx_reference += 1
                    idx_objective -= 1
                    idx_adjusted = idx_objective % len(self.vertices)
                    self.vertices[idx_adjusted].y = -self.vertices[idx_reference].y
                    self.vertices[idx_adjusted].x = self.vertices[idx_reference].x
            elif points2mirror == 'S':
                idx_reference = 0
                idx_objective = 1
                for i in range(4):
                    idx_reference -= 1
                    idx_objective += 1
                    idx_adjusted = idx_reference % len(self.vertices)
                    self.vertices[idx_objective].y = -self.vertices[idx_adjusted].y
                    self.vertices[idx_objective].x = self.vertices[idx_adjusted].x
            else:
                print('ERROR: Wrong points2mirror argument. For WE symmetry axis, only northern (N) or southern (S) points can be mirrored.')
        else:
            print('ERROR: Wrong axis argument. Only the cardinal axis NS and WE are allowed.')

    def ordinal_symmetry(self, axis, points2mirror):
        if axis == 'NWSE':
            if points2mirror == 'NE':
                quadrant, unwrap_angles = self._unwrapAngles()
                axis_angle = math.degrees(self.ref_angle[3])
                idx_objective = 0
                for i in [0, 1, 2, 3]:
                    idx_reference = i
                    idx_objective -= 1
                    idx_adjusted = idx_objective % len(self.vertices)
                    ref_point = self.vertices[idx_reference].cart2polar(Point(0, 0))
                    angle_diff = axis_angle - unwrap_angles[idx_reference]
                    if angle_diff < 0:
                        angle_diff += 360
                    new_angle = axis_angle + angle_diff
                    self.vertices[idx_adjusted].polar2cart(ref_point[0], math.radians(new_angle))
            elif points2mirror == 'SW':
                quadrant, unwrap_angles = self._unwrapAngles()
                axis_angle = math.degrees(self.ref_angle[3])
                idx_reference = 0
                for i in [0, 1, 2, 3]:
                    idx_reference -= 1
                    idx_objective = i
                    idx_reference %= len(self.vertices)
                    idx_adjusted = idx_objective % len(self.vertices)
                    ref_point = self.vertices[idx_reference].cart2polar(Point(0, 0))
                    angle_diff = axis_angle - unwrap_angles[idx_reference]
                    if angle_diff < 0:
                        angle_diff += 360
                    new_angle = axis_angle + angle_diff
                    self.vertices[idx_adjusted].polar2cart(ref_point[0], math.radians(new_angle))
            else:
                print('ERROR: Wrong points2mirror argument. For NWSE symmetry axis, only north-eastern (NE) or south-western (SW) points can be mirrored.')

        elif axis == 'NESW':
            if points2mirror == 'NW':
                quadrant, unwrap_angles = self._unwrapAngles()
                axis_angle = math.degrees(self.ref_angle[1])
                idx_objective = 2
                for i in [2, 3, 4, 5]:
                    idx_reference = i
                    idx_objective -= 1
                    idx_adjusted = idx_objective % len(self.vertices)
                    ref_point = self.vertices[idx_reference].cart2polar(Point(0, 0))
                    angle_diff = axis_angle - unwrap_angles[idx_reference]
                    if angle_diff < 0:
                        angle_diff += 360
                    new_angle = axis_angle + angle_diff
                    self.vertices[idx_adjusted].polar2cart(ref_point[0], math.radians(new_angle))
            elif points2mirror == 'SE':
                quadrant, unwrap_angles = self._unwrapAngles()
                axis_angle = math.degrees(self.ref_angle[1])
                idx_reference = 2
                for i in [2, 3, 4, 5]:
                    idx_reference -= 1
                    idx_objective = i
                    idx_reference %= len(self.vertices)
                    idx_adjusted = idx_objective % len(self.vertices)
                    ref_point = self.vertices[idx_reference].cart2polar(Point(0, 0))
                    angle_diff = axis_angle - unwrap_angles[idx_reference]
                    if angle_diff < 0:
                        angle_diff += 360
                    new_angle = axis_angle + angle_diff
                    self.vertices[idx_adjusted].polar2cart(ref_point[0], math.radians(new_angle))
            else:
                print('ERROR: Wrong points2mirror argument. For NESW symmetry axis, only north-western (NW) or south-eastern (SE) points can be mirrored.')

    def cardinal_stretch(self, side, factor):
        if side == 'N':
            P2 = self.vertices[2]
            P3 = self.vertices[3]
            delta = math.fabs(P3.x - P2.x) * (factor - 1) / 2
            for i in self.vertices:
                if i.x >= 0:
                    i.x += delta
                else:
                    i.x -= delta
            self._boundaries('S', 6, self.vertices[6], 7, self.vertices[7])
            self.stretch_factors[1] = factor

        elif side == 'S':
            P7 = self.vertices[7]
            P6 = self.vertices[6]
            delta = math.fabs(P7.x - P6.x) * (factor - 1) / 2
            for i in self.vertices:
                if i.x >= 0:
                    i.x += delta
                else:
                    i.x -= delta
            self._boundaries('N', 2, self.vertices[2], 3, self.vertices[3])
            self.stretch_factors[3] = factor

        elif side == 'E':
            P0 = self.vertices[0]
            P1 = self.vertices[1]
            delta = math.fabs(P0.y - P1.y) * (factor - 1) / 2
            for i in self.vertices:
                if i.y >= 0:
                    i.y += delta
                else:
                    i.y -= delta
            self._boundaries('W', 4, self.vertices[4], 5, self.vertices[5])
            self.stretch_factors[0] = factor

        elif side == 'W':
            P4 = self.vertices[4]
            P5 = self.vertices[5]
            delta = math.fabs(P4.y - P5.y) * (factor - 1) / 2
            for i in self.vertices:
                if i.y >= 0:
                    i.y += delta
                else:
                    i.y -= delta
            self._boundaries('E', 0, self.vertices[0], 1, self.vertices[1])
            self.stretch_factors[2] = factor

        else:
            print('ERROR: Wrong side argument. Available sides for stretching are: N, S, W and E.')

    def _ordinal_equation(self, segment_id, sa, id_point1, id_point2):
        idx_p1 = id_point1 % len(self.vertices)
        idx_p2 = id_point2 % len(self.vertices)
        idx_p1_prev = (id_point1 - 1) % len(self.vertices)
        idx_p2_next = (id_point2 + 1) % len(self.vertices)

        p1 = self.vertices[idx_p1]
        p2 = self.vertices[idx_p2]
        p1_prev = self.vertices[idx_p1_prev]
        p2_next = self.vertices[idx_p2_next]

        new_p1 = Point(0, 0)
        new_p2 = Point(0, 0)

        slope1 = (p1.y - p1_prev.y) / (p1.x - p1_prev.x)
        slope2 = (p2.y - p2_next.y) / (p2.x - p2_next.x)

        if segment_id == 'N':
            new_p1.y = sa
            new_p2.y = sa
            new_p1.x = (new_p1.y - p1.y) / slope1 + p1.x
            new_p2.x = (new_p2.y - p2.y) / slope1 + p2.x
            return new_p1, new_p2

        elif segment_id == 'S':
            new_p1.y = -sa
            new_p2.y = -sa
            new_p1.x = (new_p1.y - p1.y) / slope1 + p1.x
            new_p2.x = (new_p2.y - p2.y) / slope1 + p2.x
            return new_p1, new_p2

        elif segment_id == 'E':
            new_p1.x = sa
            new_p2.x = sa
            new_p1.y = p1.y + slope1 * (new_p1.x - p2.x)
            new_p2.y = p2.y + slope2 * (new_p2.x - p2.x)
            return new_p1, new_p2

        elif segment_id == 'W':
            new_p1.x = -sa
            new_p2.x = -sa
            new_p1.y = p1.y + slope1 * (new_p1.x - p2.x)
            new_p2.y = p2.y + slope2 * (new_p2.x - p2.x)
            return new_p1, new_p2

        else:
            return print("Incorrect segment_id. Allowed values: N, S, E, W")
