import copy
import math
import gdspy
from .Point import Point
from .Line import Line

class Polygon:
	def __init__(self, vertices):
		self.vertices = vertices
		self.gds_layer = None
		self.gds_datatype = None

	def __str__(self):
		vertex_strings = [str(vertex) for vertex in self.vertices]
		return "Polygon(" + ", ".join(vertex_strings) + ")"

	def __repr__(self):
		return f"Polygon({self.vertices})"

	def __eq__(self, other):
		if isinstance(other, Polygon):
			return self.vertices == other.vertices
		return False

	def snap_to_grid(self, grid_size):
		for vertex in self.vertices:
			vertex.snap_to_grid(grid_size)


	def perimeter(self):
		perimeter = 0.0
		num_points = len(self.vertices)
		for i in range(num_points):
			current_point = self.vertices[i]
			next_point = self.vertices[(i + 1) % num_points]
			dx = next_point.x - current_point.x
			dy = next_point.y - current_point.y
			perimeter += (dx ** 2 + dy ** 2) ** 0.5
		return perimeter

	def area(self):
		area = 0.0
		num_points = len(self.vertices)
		for i in range(num_points):
			current_point = self.vertices[i]
			next_point = self.vertices[(i + 1) % num_points]
			area += (current_point.x * next_point.y - current_point.y * next_point.x)
		return abs(area) / 2.0

	def scale(self, factor):
		centroid = self.midpoint()

		for vertex in self.vertices:
			# Calculate the vector from the centroid to the vertex
			vector = Point(vertex.x - centroid.x, vertex.y - centroid.y)

			# Scale the vector
			scaled_vector = Point(vector.x * factor, vector.y * factor)

			# Update the vertex coordinates by adding the scaled vector to the centroid
			vertex.x = centroid.x + scaled_vector.x
			vertex.y = centroid.y + scaled_vector.y

	def translate(self, dx, dy):
		for point in self.vertices:
			point.translate(dx, dy)

	def rotate_around(self, center, angle_deg):
		for point in self.vertices:
			point.rotate_around(center,angle_deg)

	def midpoint(self):
		total_x = 0.0
		total_y = 0.0
		num_points = len(self.vertices)
		for point in self.vertices:
			total_x += point.x
			total_y += point.y
		midpoint_x = total_x / num_points
		midpoint_y = total_y / num_points
		return Point(midpoint_x, midpoint_y)

	def intersects(self, other_polygon):
		for i in range(len(self.vertices)):
			current_point = self.vertices[i]
			next_point = self.vertices[(i + 1) % len(self.vertices)]
			for j in range(len(other_polygon.vertices)):
				other_current_point = other_polygon.vertices[j]
				other_next_point = other_polygon.vertices[(j + 1) % len(other_polygon.vertices)]
				if self._do_lines_intersect(current_point, next_point, other_current_point, other_next_point):
					return True
		return False

	def _do_lines_intersect(self, p1, p2, q1, q2):
		def _orientation(p, q, r):
			val = (q.y - p.y) * (r.x - q.x) - (q.x - p.x) * (r.y - q.y)
			if val == 0:
				return 0  # Collinear
			elif val > 0:
				return 1  # Clockwise orientation
			else:
				return 2  # Counterclockwise orientation

		o1 = _orientation(p1, p2, q1)
		o2 = _orientation(p1, p2, q2)
		o3 = _orientation(q1, q2, p1)
		o4 = _orientation(q1, q2, p2)

		if o1 != o2 and o3 != o4:
			return True

		if o1 == 0 and self._on_segment(p1, q1, p2):
			return True

		if o2 == 0 and self._on_segment(p1, q2, p2):
			return True

		if o3 == 0 and self._on_segment(q1, p1, q2):
			return True

		if o4 == 0 and self._on_segment(q1, p2, q2):
			return True

		return False

	def _on_segment(self, p, q, r):
		return (min(p.x, r.x) <= q.x <= max(p.x, r.x) and
		        min(p.y, r.y) <= q.y <= max(p.y, r.y))

	def is_inside(self, other_polygon):
		for vertex in self.vertices:
			if not other_polygon.contains_point(vertex):
				return False
		return True

	def contains_point(self, point):
		num_vertices = len(self.vertices)
		inside = False

		p1 = self.vertices[0]
		for i in range(num_vertices + 1):
			p2 = self.vertices[i % num_vertices]
			if point.y > min(p1.y, p2.y):
				if point.y <= max(p1.y, p2.y):
					if point.x <= max(p1.x, p2.x):
						if p1.y != p2.y:
							xinters = (point.y - p1.y) * (p2.x - p1.x) / (p2.y - p1.y) + p1.x
							if p1.x == p2.x or point.x <= xinters:
								inside = not inside
			p1 = p2

		return inside

	def bounding_box(self):
		min_x = float('inf')
		min_y = float('inf')
		max_x = float('-inf')
		max_y = float('-inf')

		for vertex in self.vertices:
			if vertex.x < min_x:
				min_x = vertex.x
			if vertex.y < min_y:
				min_y = vertex.y
			if vertex.x > max_x:
				max_x = vertex.x
			if vertex.y > max_y:
				max_y = vertex.y

		bottom_left = Point(min_x, min_y)
		bottom_right = Point(max_x, min_y)
		top_right = Point(max_x, max_y)
		top_left = Point(min_x, max_y)

		return bottom_left, bottom_right, top_right, top_left

	def _get_edges(self):
		num_vertices = len(self.vertices)
		edges = []

		for i in range(num_vertices):
			current_vertex = self.vertices[i]
			next_vertex = self.vertices[(i + 1) % num_vertices]
			edges.append((current_vertex, next_vertex))

		return edges


	def _is_near_edge(self, other_polygon, distance_threshold):
		for edge1 in self._get_edges():
			for edge2 in other_polygon._get_edges():
				if self._edges_are_near(edge1, edge2, distance_threshold, other_polygon):
					return True
		return False

	def _edges_are_near(self, edge1, edge2, distance_threshold, other_polygon):
		edge1_start, edge1_end = edge1
		edge2_start, edge2_end = edge2

		# Calculate the distance between the edges
		distance = self._point_to_edge_distance(edge1_start, edge2)

		if distance <= distance_threshold:
			return True

		distance = self._point_to_edge_distance(edge1_end, edge2)

		if distance <= distance_threshold:
			return True

		distance = other_polygon._point_to_edge_distance(edge2_start, edge1)

		if distance <= distance_threshold:
			return True

		distance = other_polygon._point_to_edge_distance(edge2_end, edge1)

		if distance <= distance_threshold:
			return True

		return False

	def _point_to_edge_distance(self, point, edge):
		edge_start, edge_end = edge

		# Calculate the vector representing the edge
		edge_vector = Point(edge_end.x - edge_start.x, edge_end.y - edge_start.y)

		# Calculate the vector from the edge start to the point
		point_vector = Point(point.x - edge_start.x, point.y - edge_start.y)

		# Calculate the dot product of the edge vector and point vector
		dot_product = edge_vector.x * point_vector.x + edge_vector.y * point_vector.y

		# Check the winding order to determine if the point is on the correct side of the edge
		if dot_product <= 0:
			# The point is on the opposite side or collinear with the edge
			return point.distance(edge_start)

		edge_length_squared = edge_vector.x ** 2 + edge_vector.y ** 2

		if dot_product >= edge_length_squared:
			# The point is beyond the end of the edge
			return point.distance(edge_end)

		# Calculate the projection value
		projection = dot_product / edge_length_squared

		# Calculate the projected vector onto the edge vector
		projected_vector = Point(edge_vector.x * projection, edge_vector.y * projection)

		# Calculate the perpendicular distance from the point to the edge
		perpendicular_distance = point_vector.distance(projected_vector)

		return perpendicular_distance


	def line_angles(self):
		angles = []
		num_points = len(self.vertices)
		for i in range(num_points):
			current_point = self.vertices[i]
			next_point = self.vertices[(i + 1) % num_points]
			dx = next_point.x - current_point.x
			dy = next_point.y - current_point.y
			angle = math.atan2(dy, dx)
			angles.append(math.degrees(angle))
		return angles


	def generate_staircase_lines(self, step_size):
		num_points = len(self.vertices)
		new_vertices = []

		for i in range(num_points):
			current_point = self.vertices[i]
			next_point = self.vertices[(i + 1) % num_points]
			line = Line(current_point, next_point)
			
			staircase_line = line.generate_staircase_line(step_size)
			new_vertices.extend(staircase_line[1:])  # Exclude the first point (already added in previous segment)
			
		self.vertices = new_vertices



	def copy(self):
		copied_vertices = [Point(vertex.x, vertex.y) for vertex in self.vertices]
		return Polygon(copied_vertices)

	def to_gdspy_polygon(self, layer, datatype):
		points = [(vertex.x, vertex.y) for vertex in self.vertices]
		return gdspy.Polygon(points, layer, datatype)


	@classmethod
	def from_gdspy_polygon(cls, gdspy_polygon):
		points = [Point(point[0], point[1]) for point in gdspy_polygon.points]
		return cls(points)

	@staticmethod
	def copy_polygons(polygons):
		copied_polygons = []
		for polygon in polygons:
			copied_polygons.append(copy.deepcopy(polygon))
		return copied_polygons



	@staticmethod
	def move_polygons(polygons, dx, dy):
		for polygon in polygons:
			polygon.translate(dx, dy)

	@staticmethod
	def rotate_polygons(polygons, center, angle_deg):
		for polygon in polygons:
			polygon.rotate_around(center, angle_deg)

	@staticmethod
	def move_polygons_to_point_and_rotate(polygons, reference_point , new_point, angle_deg=0):

		dx = new_point.x - reference_point.x
		dy = new_point.y - reference_point.y

		for polygon in polygons:
			polygon.translate(dx, dy)

		Polygon.rotate_polygons(polygons, new_point, angle_deg)

	@staticmethod
	def move_polygons_on_line(polygons, current_reference_point, line, offsetX=0, offsetY=0):
		# Calculate the midpoint of the line
		midpoint = line.midpoint()

		# Calculate the vector representing the line
		line_vector = Point(line.point2.x - line.point1.x, line.point2.y - line.point1.y)

		# Calculate the perpendicular angle
		angle_radians = math.atan2(-line_vector.x, line_vector.y)
		angle_degrees = math.degrees(angle_radians)

		# Calculate the unit vector along the line
		line_unit_vector = line_vector.normalize()

		# Calculate the offset vectors
		offset_vector_x = Point(line_unit_vector.x * offsetX, line_unit_vector.y * offsetX)
		offset_vector_y = Point(line_unit_vector.y * offsetY, -line_unit_vector.x * offsetY)

		# Apply the offset vectors to the midpoint
		offset_midpoint = Point(midpoint.x + offset_vector_x.x + offset_vector_y.x,
		                        midpoint.y + offset_vector_x.y + offset_vector_y.y)

		# Place the polygons on the line using the move_polygons_on_point function
		Polygon.move_polygons_to_point_and_rotate(polygons, current_reference_point, offset_midpoint, angle_degrees - 90)



	@staticmethod
	def bounding_box_polygons(polygons):
		min_x = float('inf')
		min_y = float('inf')
		max_x = float('-inf')
		max_y = float('-inf')

		for polygon in polygons:
			bbox = polygon.bounding_box()
			for point in bbox:
				min_x = min(min_x, point.x)
				min_y = min(min_y, point.y)
				max_x = max(max_x, point.x)
				max_y = max(max_y, point.y)

		bottom_left = Point(min_x, min_y)
		bottom_right = Point(max_x, min_y)
		top_right = Point(max_x, max_y)
		top_left = Point(min_x, max_y)

		return [bottom_left, bottom_right, top_right, top_left]


