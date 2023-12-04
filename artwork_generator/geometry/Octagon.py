from .Point import Point
from .Polygon import Polygon
import copy
import math

class Octagon:
	def __init__(self, apothem_ref):
		self.apothem_ref = apothem_ref  # Stores reference apothem for regular Octagon.
		outer_radius = apothem_ref / math.cos(math.pi / 8) # Calculates outer radius.
		self.vertices = [] # List of cartesian points conforming the octagon as Point instances.
		self.ref_angle = [] # List containing the apothem angles.

		self.boundaries_enable = 1 # Enables (1, default) or disable (0) boundary conditions for irregular octagon design.
		# self.factors stores the factors to build the octagon at each modification. Initialized to 1.
		self.factors = [1]*8
		# self.stretch_factors stores the factors applied in stretch method. Initialized to 1.
		self.stretch_factors = [1]*4

		for i in range(8):
			x = outer_radius * math.cos(-math.pi / 8)
			y = outer_radius * math.sin(-math.pi / 8)
			p = Point(x, y)
			pOrigin = Point(0, 0)
			p.rotate_around(pOrigin, 45 * i)
			self.vertices.append(Point(p.x, p.y))
			self.ref_angle.append(math.pi/4*i)

	def info(self):
		segment_id = ["E", "NE", "N", "NW", "W", "SW", "S", "SE"]
		point_id = ["P0", "P1", "P2", "P3", "P4", "P5", "P6", "P7"]
		perimeter, area = self.geometry()
		min, max = self.allowed_factors()

		print("_____________________________")
		print("OCTAGON DATA\r\n_____________________________")
		print("Reference apothem: " + str(self.apothem_ref))
		print("Perimeter: " + str(round(perimeter,2)))
		print("Area: " + str(round(area,2)))
		print("Current apothem factors [E, NE, N, NW, W, SW, S, SE]: " + str(self.factors))
		print("Allowed factor range per side [min - max]:")
		for i in range(8):
			entry = segment_id[i]+": "+ "[ " + str(min[i]) + "-" + str(max[i]) + " ]"
			print(entry)

		print("Stretch factors [E, N, W, S]: " + str(self.stretch_factors))
		print("Cartesian coordinates: ")
		for i in range(8):
			entry2 = point_id[i]+": " + str((round(self.vertices[i].x,2),round(self.vertices[i].y,2)))
			print(entry2)

	def geometry(self):
		segment_length = []

		# Calculate perimeter as the sum of each segment
		for i in range(8):
			idx_next = i+1
			idx_next %= len(self.vertices)

			p_current = self.vertices[i]
			p_next = self.vertices[idx_next]
			segment_length.append(p_current.distance(p_next))

		perimeter = sum(segment_length)

		# Calculate area as the difference between the perfect square and the ordinal empty triangles
		perfect_square = math.fabs(self.vertices[2].y-self.vertices[7].y)*math.fabs(self.vertices[0].x-self.vertices[4].x)
		triangle_NE = math.fabs(self.vertices[2].y-self.vertices[1].y)*math.fabs(self.vertices[2].x-self.vertices[1].x)/2
		triangle_NW = math.fabs(self.vertices[3].y-self.vertices[4].y)*math.fabs(self.vertices[3].x-self.vertices[4].x)/2
		triangle_SW = math.fabs(self.vertices[5].y-self.vertices[6].y)*math.fabs(self.vertices[5].x-self.vertices[6].x)/2
		triangle_SE = math.fabs(self.vertices[7].y-self.vertices[0].y)*math.fabs(self.vertices[7].x-self.vertices[0].x)/2

		area = perfect_square - (triangle_NE + triangle_NW + triangle_SW + triangle_SE)


		return perimeter, area

	def modify_apothem(self, factor):
		# Changes regular octagon based on an input list of apothem scaling factors: "factor"
		# factor = [E,NE,N,NW,W,SW,S,SE]

		self.vertices[0], self.vertices[1] = self.E(factor[0])
		self.vertices[1], self.vertices[2] = self.NE(factor[1])
		self.vertices[2], self.vertices[3] = self.N(factor[2])
		self.vertices[4], self.vertices[3] = self.NW(factor[3])
		self.vertices[4], self.vertices[5] = self.W(factor[4])
		self.vertices[5], self.vertices[6] = self.SW(factor[5])
		self.vertices[6], self.vertices[7] = self.S(factor[6])
		self.vertices[0], self.vertices[7] = self.SE(factor[7])

		self.factors = factor

	def activate_boundaries(self,input):
		# Enables (input = 1) or disables (input = 0) boundaries for irregular octagon design.
		if input == 1 or input == 0:
			self.boundaries_enable = input
		else:
			msg = "ERROR: .activate_boundaries only allows 1 or 0. This method enables (1) or disables (0) boundary conditions for irregular octagon design."
			return print(msg)

	def NE(self, scaling_factor):
		# NE segment defined by points P1 and P2. Constrained by points P3 and P0.
		# Scaled apothem (regular octagon reference)
		sa = scaling_factor*self.apothem_ref
		# Reference angle for the NE apothem
		ref_angle = self.ref_angle[1]
		# Calculate the new points P1 and P2

		new_P1, new_P2 = self._cardinal_equation(sa,ref_angle,1,2)

		# Verify boundary conditions if enabled.
		self._boundaries('NE', 1, new_P1, 2, new_P2)
		# Return the new points
		return new_P1, new_P2

	def NW(self, scaling_factor):
		# NW segment defined by points P3 and P4. Constrained by points P2 and P5.
		# Scaled apothem (regular octagon reference)
		sa = scaling_factor*self.apothem_ref
		# Reference angle for the NW apothem
		ref_angle = self.ref_angle[3]
		# Calculate the new points P4 and P3
		new_P4, new_P3 = self._cardinal_equation(sa, ref_angle, 4, 3)
		# Verify boundary conditions if enabled.
		self._boundaries('NW', 3, new_P3, 4, new_P4)
		# Return the new points
		return new_P4, new_P3

	def SW(self, scaling_factor):
		# SW segment defined by points P5 and P6. Constrained by points P4 and P7.
		# Scaled apothem (regular octagon reference)
		sa = scaling_factor*self.apothem_ref
		# Reference angle for the SW apothem
		ref_angle = self.ref_angle[5]
		# Calculate new points P5 and P6
		new_P5, new_P6 = self._cardinal_equation(sa, ref_angle, 5, 6)
		# Verify boundary conditions if enabled.
		self._boundaries('SW', 5, new_P5, 6, new_P6)
		# Return the new points
		return new_P5, new_P6

	def SE(self, scaling_factor):
		# SW segment defined by points P7 and P0. Constrained by points P6 and P1.
		# Scaled apothem (regular octagon reference)
		sa = scaling_factor*self.apothem_ref
		# Reference angle for the SW apothem
		ref_angle = self.ref_angle[7]
		# Calculate new points P7 and P0
		new_P0, new_P7 = self._cardinal_equation(sa, ref_angle, 0, 7)
		# Verify boundary conditions if enabled.
		self._boundaries('SE', 7, new_P7, 0, new_P0)
		# Return new points
		return new_P0, new_P7

	def E(self,scaling_factor):
		# E segment defined by points P0 and P1. Constrained by points P2 and P7.
		# Scaled apothem (regular octagon reference)
		sa = scaling_factor*self.apothem_ref
		# Calculate the new P0 and P1
		new_P0, new_P1 = self._ordinal_equation('E', sa, 0, 1)
		# Verify boundary conditions if enabled.
		self._boundaries('E', 0, new_P0, 1, new_P1)
		# Update P1 and P0 vertices
		return new_P0, new_P1

	def W(self, scaling_factor):
		# W segment defined by points P4 and P5. Constrained by points P3 and P6.
		# Scaled apothem (regular octagon reference)
		sa = scaling_factor * self.apothem_ref
		# Calculate the new P4 and P5
		new_P4, new_P5 = self._ordinal_equation('W', sa, 4, 5)
		# Verify boundary conditions if enabled.
		self._boundaries('W', 4, new_P4, 5, new_P5)
		# Update P4 and P5 vertices
		return new_P4, new_P5

	def N(self, scaling_factor):
		# N segment defined by points P2 and P3. Constrained by points P1 and P4.
		# Scaled apothem (regular octagon reference)
		sa = scaling_factor * self.apothem_ref
		# Calculate the new P2 and P3
		new_P2, new_P3 = self._ordinal_equation('N', sa, 2, 3)
		# Verify boundary conditions if enabled.
		self._boundaries('N', 2, new_P2, 3, new_P3)
		# Update P2 and P3 vertices
		return new_P2, new_P3
	def S(self, scaling_factor):
		# S segment defined by points P6 and P7. Constrained by points P0 and P5.
		# Scaled apothem (regular octagon reference)
		sa = scaling_factor * self.apothem_ref
		# Calculate the new P6 and P7
		new_P6, new_P7 = self._ordinal_equation('S', sa, 6, 7)
		# Verify boundary conditions if enabled.
		self._boundaries('S', 6, new_P6, 7, new_P7)
		# Update P6 and P7 vertices
		return new_P6, new_P7

	def cardinal_symmetry(self, axis, points2mirror):
		match axis:
			case 'NS':
				match points2mirror:
					case 'E':
						idx_objective = 7
						for i in [-1,0,1,2]:
							idx_reference = i
							idx_objective -= 1
							idx_reference %= len(self.vertices)
							idx_adjusted = idx_objective % len(self.vertices)
							self.vertices[idx_adjusted].y = self.vertices[idx_reference].y
							self.vertices[idx_adjusted].x = -self.vertices[idx_reference].x
					case 'W':
						idx_reference = 7
						for i in [-1, 0, 1, 2]:
							idx_reference -= 1
							idx_objective = i
							idx_reference %= len(self.vertices)
							idx_adjusted = idx_objective % len(self.vertices)
							self.vertices[idx_adjusted].y = self.vertices[idx_reference].y
							self.vertices[idx_adjusted].x = -self.vertices[idx_reference].x
					case other:
						print('ERROR: Wrong points2mirror argument. For NS symmetry axis, only western (W) or eastern (E) points can be mirrored.')
			case 'WE':
				match points2mirror:
					case 'N':
						idx_reference = 0
						idx_objective = 1
						for i in range(4):
							idx_reference += 1
							idx_objective -= 1
							idx_adjusted = idx_objective % len(self.vertices)
							print(idx_reference,idx_adjusted)
							self.vertices[idx_adjusted].y = -self.vertices[idx_reference].y
							self.vertices[idx_adjusted].x = self.vertices[idx_reference].x
					case 'S':
						idx_reference = 0
						idx_objective = 1
						for i in range(4):
							idx_reference -= 1
							idx_objective += 1
							idx_adjusted = idx_reference % len(self.vertices)
							self.vertices[idx_objective].y = -self.vertices[idx_adjusted].y
							self.vertices[idx_objective].x = self.vertices[idx_adjusted].x
					case other:
						print('ERROR: Wrong points2mirror argument. For WE symmetry axis, only northern (N) or southern (S) points can be mirrored.')
			case other:
				print('ERROR: Wrong axis argument. Only the cardinal axis NS and WE are allowed.')
	def ordinal_symmetry(self, axis, points2mirror):
		match axis:
			case 'NWSE':
				match points2mirror:
					case 'NE':
						quadrant, unwrap_angles = self._unwrapAngles()
						axis_angle = math.degrees(self.ref_angle[3])
						idx_objective = 0
						for i in [0,1,2,3]:
							idx_reference = i
							idx_objective -= 1
							idx_adjusted = idx_objective % len(self.vertices)
							ref_point = self.vertices[idx_reference].cart2polar(Point(0,0))
							angle_diff = axis_angle - unwrap_angles[idx_reference]
							if angle_diff<0:
								angle_diff += 360
							new_angle = axis_angle + angle_diff
							self.vertices[idx_adjusted].polar2cart(ref_point[0],math.radians(new_angle))
					case 'SW':
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
					case other:
						print('ERROR: Wrong points2mirror argument. For NWSE symmetry axis, only north-eastern (NE) or south-western (SW) points can be mirrored.')
			case 'NESW':
				match points2mirror:
					case 'NW':
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
					case 'SE':
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
					case other:
						print('ERROR: Wrong points2mirror argument. For NESW symmetry axis, only north-western (NW) or south-eastern (SE) points can be mirrored.')

	def cardinal_stretch_all(self,factor):
		self.cardinal_stretch('E',factor[0])
		self.cardinal_stretch('N',factor[1])
		self.cardinal_stretch('W',factor[2])
		self.cardinal_stretch('S',factor[3])

	def cardinal_stretch(self,side,factor):
		match side:
			case 'N':
				P2 = self.vertices[2]
				P3 = self.vertices[3]
				delta = math.fabs(P3.x-P2.x)*(factor-1)/2
				for i in self.vertices:
					if i.x >= 0:
						i.x += delta
					else:
						i.x -= delta
				self._boundaries('S', 6, self.vertices[6], 7, self.vertices[7])
				self.stretch_factors[1] = factor
			case 'S':
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
			case 'E':
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
			case 'W':
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
			case other:
				print('ERROR: Wrong side argument. Available sides for stretching are: N, S, W and E.')

	def get_offset_points(self, distance):
		vertices = []
		for i in range(8):
			vertices.append(Point(self.vertices[i].x, self.vertices[i].y))

		poly = Polygon(vertices)
		poly.scale((distance + self.apothem_ref) / self.apothem_ref)
		return poly.vertices

	def get_offset_vertices(self, thickness):
		rect = lambda x,m,n: m*x+n
		rect_inv = lambda y,m,n: (y-n)/m
		slope = lambda p1,p2: (p1.x-p2.x)/(p1.y-p2.y)
		n = lambda p,m: p.y-m*p.x

		new_vertices = []
		inter = []
		# new_factor = []
		new_vertices = copy.deepcopy(self.vertices)

		# Rect segment NE
		slope_ne = slope(new_vertices[2], new_vertices[1])
		n_ne = n(new_vertices[1], slope_ne)
		delta_nne = thickness / math.cos(math.pi / 2 - self.ref_angle[1])
		new_nne = n_ne + delta_nne

		# Rect segment SE
		slope_se = slope(new_vertices[7], new_vertices[0])
		n_se = n(new_vertices[0], slope_se)
		delta_nse = thickness / math.cos(math.pi / 2 - self.ref_angle[7])
		new_nse = n_se + delta_nse

		# Rect segment NW
		slope_nw = slope(new_vertices[3], new_vertices[4])
		n_nw = n(new_vertices[4], slope_nw)
		delta_nnw = thickness / math.cos(math.pi - self.ref_angle[3])
		new_nnw = n_nw + delta_nnw

		# Rect segment SW
		slope_sw = slope(new_vertices[5], new_vertices[6])
		n_sw = n(new_vertices[5], slope_sw)
		delta_nsw = thickness / math.cos(math.pi - self.ref_angle[5])
		new_nsw = n_sw - delta_nsw


		# Update E segment
		new_vertices[0].x += thickness
		new_vertices[1].x += thickness

		new_vertices[1].y = rect(new_vertices[1].x, slope_ne, new_nne)
		new_vertices[0].y = rect(new_vertices[0].x, slope_se, new_nse)

		# Update N segment
		new_vertices[2].y += thickness
		new_vertices[3].y += thickness

		new_vertices[2].x = rect_inv(new_vertices[2].y, slope_ne, new_nne)
		new_vertices[3].x = rect_inv(new_vertices[3].y, slope_nw, new_nnw)

		# Update W segment
		new_vertices[4].x -= thickness
		new_vertices[5].x -= thickness

		new_vertices[4].y = rect(new_vertices[4].x, slope_nw, new_nnw)
		new_vertices[5].y = rect(new_vertices[5].x, slope_sw, new_nsw)
		# Update S segment
		new_vertices[6].y -= thickness
		new_vertices[7].y -= thickness

		new_vertices[6].x = rect_inv(new_vertices[6].y, slope_sw, new_nsw)
		new_vertices[7].x = rect_inv(new_vertices[7].y, slope_se, new_nse)

		print(self.vertices)
		print(new_vertices)
		return new_vertices

	def allowed_factors(self):
		quadrant, angles = self._unwrapAngles()
		min_factor = []
		max_factor = []

		print(angles)
		for i in range(8):
			idx_lim = i+1
			idx_next = i+2
			idx_prev = i-1

			idx_lim %= len(self.vertices)
			idx_next %= len(self.vertices)
			idx_prev %= len(self.vertices)

			# Estimates the minimum factor
			diff1 = angles[idx_next] - angles[idx_lim]
			diff2 = angles[i] - angles[idx_prev]
			if diff1 < 0:
				diff1 += 360
			if diff2 < 0:
				diff2 += 360

			if diff1 <= diff2:
				min_limit_point = self.vertices[idx_next]
			else:
				min_limit_point = self.vertices[idx_prev]

			diff3 = self.ref_angle[i] - min_limit_point.cart2polar(Point(0,0))[1]
			aux = min_limit_point.cart2polar(Point(0,0))[0]*math.cos(diff3)
			min_factor.append(round(aux/self.apothem_ref,2))

			# Estimates the maximum factor
			p1_next = self.vertices[idx_next]
			p1_lim = self.vertices[idx_lim]
			p2_lim = self.vertices[i]
			p2_prev = self.vertices[idx_prev]
			intersect = Point(0, 0)

			if (round(p1_next.x) != round(p1_lim.x)) and (round(p2_prev.x) != round(p2_lim.x)):
				m1 = (p1_next.y-p1_lim.y)/(p1_next.x-p1_lim.x)
				m2 = (p2_prev.y-p2_lim.y)/(p2_prev.x-p2_lim.x)

				n1 = p1_lim.y - m1*p1_lim.x
				n2 = p2_lim.y - m2*p2_lim.x

				intersect.x = (n2-n1)/(m1-m2)
				intersect.y = m1*intersect.x + n1
			else:
				if round(p1_next.x) == round(p1_lim.x):
					intersect.x = p1_lim.x
					intersect.y = p2_lim.y
				else:
					intersect.x = p2_lim.x
					intersect.y = p1_lim.y
			diff3 = self.ref_angle[i]-intersect.cart2polar(Point(0,0))[1]
			max_factor.append(round(intersect.cart2polar(Point(0,0))[0]*math.cos(diff3)/self.apothem_ref,2))

		return min_factor, max_factor

	def _cardinal_equation(self, sa, ref_angle, id_point1, id_point2):
		# This function calculates the new pair of points new_p1 and new_p2 defining a cardinal segment based
		# on a scaling factor.

		# Determine point indexes
		idx_p1 = id_point1 % len(self.vertices)
		idx_p2 = id_point2 % len(self.vertices)

		# Getting polar coordinates of referred input points
		p1 = self.vertices[idx_p1].cart2polar(Point(0, 0))
		p2 = self.vertices[idx_p2].cart2polar(Point(0, 0))

		# Initializing new points
		new_p1 = Point(0, 0)
		new_p2 = Point(0, 0)

		# Calculate the new angle for both points based on the scaling factors
		new_angle1 = math.atan((sa / (p1[0] * math.cos(p1[1])) - math.cos(ref_angle)) / math.sin(ref_angle))
		new_angle2 = math.atan(((sa / (p2[0] * math.sin(p2[1])) - math.sin(ref_angle)) / math.cos(ref_angle)) ** (-1))

		# Calculate the new polar radius for both points based on the calculated angles.
		new_r1 = p1[0] * math.cos(p1[1]) / math.cos(new_angle1)
		new_r2 = p2[0] * math.sin(p2[1]) / math.sin(new_angle2)

		# Updating the new points
		new_p1.polar2cart(new_r1, new_angle1)
		new_p2.polar2cart(new_r2, new_angle2)

		return new_p1, new_p2
	def _ordinal_equation(self, segment_id, sa, id_point1, id_point2):
		# This function calculates the new pair of points new_p1 and new_p2 defining an ordinal segment based
		# on a scaling factor.

		# Determine point indexes
		idx_p1 = id_point1 % len(self.vertices)
		idx_p2 = id_point2 % len(self.vertices)
		idx_p1_prev = (id_point1-1) % len(self.vertices)
		idx_p2_next = (id_point2+1) % len(self.vertices)

		# Store points
		p1 = self.vertices[idx_p1]
		p2 = self.vertices[idx_p2]
		p1_prev = self.vertices[idx_p1_prev]
		p2_next = self.vertices[idx_p2_next]

		# Initialize new points
		new_p1 = Point(0, 0)
		new_p2 = Point(0, 0)

		# Calculate slopes
		slope1 = (p1.y-p1_prev.y)/(p1.x-p1_prev.x)
		slope2 = (p2.y-p2_next.y)/(p2.x-p2_next.x)

		# Update new points depending on segment_id
		match segment_id:
			case 'N':
				new_p1.y = sa
				new_p2.y = sa

				new_p1.x = (new_p1.y - p1.y)/slope1 + p1.x
				new_p2.x = (new_p2.y - p2.y)/slope1 + p2.x

				return new_p1, new_p2
			case 'S':
				new_p1.y = -sa
				new_p2.y = -sa

				new_p1.x = (new_p1.y - p1.y)/slope1 + p1.x
				new_p2.x = (new_p2.y - p2.y)/slope1 + p2.x

				return new_p1, new_p2
			case 'E':
				new_p1.x = sa
				new_p2.x = sa

				new_p1.y = p1.y + slope1 * (new_p1.x - p2.x)
				new_p2.y = p2.y + slope2 * (new_p2.x - p2.x)

				return new_p1, new_p2
			case 'W':
				new_p1.x = -sa
				new_p2.x = -sa

				new_p1.y = p1.y + slope1 * (new_p1.x - p2.x)
				new_p2.y = p2.y + slope2 * (new_p2.x - p2.x)

				return new_p1, new_p2
			case other:
				return print("Incorrect segment_id. Allowed values: N, S, E, W")

	def _unwrapAngles(self):
		quadrant = []
		copy_vertices = self.vertices
		vert_angles = []

		for i in copy_vertices:
			if i.x >= 0:
				if i.y >= 0:
					quadrant.append(1)
					vert_angles.append(math.degrees(i.cart2polar(Point(0, 0))[1]))
				else:
					quadrant.append(4)
					test = i.cart2polar(Point(0, 0))[1]
					if test >= 3 * math.pi / 2 and test < 2 * math.pi:
						vert_angles.append(math.degrees(test))
					else:
						vert_angles.append(math.degrees(2 * math.pi + test))
			else:
				if i.y >= 0:
					quadrant.append(2)
					test = i.cart2polar(Point(0, 0))[1]
					if test <= math.pi and test > math.pi / 2:
						vert_angles.append(math.degrees(test))
					else:
						vert_angles.append(math.degrees(math.pi + test))
				else:
					quadrant.append(3)
					test = i.cart2polar(Point(0, 0))[1]
					if test < 3 * math.pi / 2 and test > math.pi:
						vert_angles.append(math.degrees(test))
					else:
						vert_angles.append(math.degrees(2 * math.pi + test))
		return quadrant, vert_angles
	def _boundaries(self, segment_id, id_point1, new_point1, id_point2, new_point2):
	# Configures the boundary conditions. If enabled with the method .boundaries_enable, this code will not
	# allow a change in the points if they challenge the octagon consistency.

		if self.boundaries_enable:
			print('\033[93m'+"Evaluating boundary conditions for segment "+segment_id+"."+'\033[0m')
			copy_vertices = self.vertices
			copy_vertices[id_point1] = new_point1
			copy_vertices[id_point2] = new_point2

			quadrant, vert_angles = self._unwrapAngles()

			id_point1_next = (id_point1+1) % len(vert_angles)
			id_point1_prev = (id_point1-1) % len(vert_angles)

			diff1 = vert_angles[id_point1_next]-vert_angles[id_point1_prev]
			diff2 = vert_angles[id_point1_next]-vert_angles[id_point1]

			if (quadrant[id_point1] == 4) and (quadrant[id_point1_next] == 1 or quadrant[id_point1_next] == 2):
				diff1 += 360
				diff2 += 360

			if (quadrant[id_point1] == 1 or quadrant[id_point1] == 2) and quadrant[id_point1_prev] == 4:
				diff1 += 360

			if (quadrant[id_point1] == 3) and quadrant[id_point1_next] == 1:
				diff1 += 360
				diff2 += 360

			particular_condition1 = (quadrant[id_point1] == 1 and quadrant[id_point1_next] == 4)

			if diff1 <= diff2 or diff2<0 or particular_condition1:
				msg1 = "Exceeded boundary conditions for" + " point P" + str(id_point1) + " in segment " + segment_id + "."
				raise Exception(msg1)

			id_point2_next = (id_point2+1) % len(vert_angles)
			id_point2_prev = (id_point2-1) % len(vert_angles)

			diff1 = vert_angles[id_point2_next] - vert_angles[id_point2_prev]
			diff2 = vert_angles[id_point2_next] - vert_angles[id_point2]

			if (quadrant[id_point2] == 4) and (quadrant[id_point2_next] == 1 or quadrant[id_point2_next] == 2):
				diff1 += 360
				diff2 += 360
			if (quadrant[id_point2] == 1 or quadrant[id_point2] == 2) and quadrant[id_point2_prev] == 4:
				diff1 += 360
			if (quadrant[id_point2] == 3) and quadrant[id_point2_next] == 1:
				diff1 += 360
				diff2 += 360
			if (quadrant[id_point2] == 1) and quadrant[id_point2_prev] == 3:
				diff1 += 360

			particular_condition2 = (quadrant[id_point2] == 1 and quadrant[id_point2_next] == 4)

			if diff1 <= diff2 or diff2 < 0 or particular_condition2:
				msg2 = "Exceeded boundary conditions for" + " point P" + str(id_point2)+ " in segment " + segment_id + "."
				raise Exception(msg2)

			print('\033[92m'+segment_id + " segment was drawn successfully."+'\033[0m')
		else:
			print('\033[95m'+"Ignoring boundary conditions for segment "+segment_id+"."+'\033[0m')