import copy
import os.path
import sys
import argparse 


from geometry.Line import Line
from geometry.Octagon import Octagon 
from geometry.Polygon import Polygon
from geometry.Point import Point


import gdspy
import json
import math


class inductiveComp:
	def __init__(self, InductorData, output_path, output_name):

		#InductorData = json.loads(InductorDataJSON)
		# Print output_path and output_name if they are defined
		


		self.Parameters = InductorData["parameters"]
		self.Segments = InductorData["segments"]
		self.Bridges = InductorData["bridges"]
		self.Arms = InductorData["arms"]
		self.Ports = InductorData["ports"]["data"]
		self.Via = InductorData["via"]
		self.ViaPadStack = InductorData["viaPadStack"]
		self.GuardRing = InductorData["guardRing"]
		self.Layers = InductorData["layer"]
		self.T = self.Parameters["width"]  # the width of the conductors
		self.S = self.Parameters["spacing"]  # spacing between the conductors
		self.C = self.Parameters["corners"]
		self.N = self.Parameters["rings"]
		self.ref_Octagon = Octagon(self.Parameters["apothem"])
		
		self.lib = gdspy.GdsLibrary()
		self.cell = self.lib.new_cell(self.Parameters["name"])

		self.segment_gds_items = []
		self.bridge_gds_items = []
		self.arm_gds_items = []
		self.via_gds_items = []
		self.guard_ring_gds_items = []
		self.dummy_fills_gds_items = []
		self.port_gds_items = []

		self.port_info = []

		print("CONURE")

		self._generate_segment_items()
		self._generate_bridge_items()
		self._generate_bridge_extensions_items()
		self._generate_arm_items()
		self._generate_guardRing_items()
		self._generate_dummy_fills()
		self._generate_port_items()

		self._draw_items_to_gds(self.segment_gds_items,True, 0.005)
		self._draw_items_to_gds(self.bridge_gds_items,True, 0.005)
		self._draw_items_to_gds(self.arm_gds_items,True, 0.005)
		self._draw_items_to_gds(self.guard_ring_gds_items,True, 0.005)
		self._draw_items_to_gds(self.via_gds_items,True, 0.005,)
		self._draw_items_to_gds(self.dummy_fills_gds_items,True, 0.005, True, 0.02)

		gdsOutputPath = []
		gdsOutputName = []
		if output_path:
			gdsOutputPath = output_path
		else:
			gdsOutputPath = self.Parameters["outputDir"]

		if output_name:
			gdsOutputName = output_name
		else:
			gdsOutputName = self.Parameters["name"]

		#if not os.path.exists(self.Parameters["outputDir"]):
		#	os.makedirs(self.Parameters["outputDir"] )
		if not os.path.exists(gdsOutputPath):
			os.makedirs(gdsOutputPath )

		self.lib.write_gds(gdsOutputPath + "/" + gdsOutputName + ".gds")
		self.cell.write_svg(gdsOutputPath + "/" + gdsOutputName + ".svg")
		#self.lib.write_gds(self.Parameters["outputDir"] + "/" + self.Parameters["name"] + ".gds")
		#self.cell.write_svg(self.Parameters["outputDir"] + "/" + self.Parameters["name"] + ".svg")
		#gdspy.LayoutViewer(self.lib)

	def _generate_segment_items(self):
		pass
		config = self.Segments["config"]
		SegData = self.Segments["data"]
		# print(SegData)

		for sgName, sgData in SegData.items():
			segId = sgData["id"]
			for ring in range(len(sgData["group"])):
				segData = sgData["group"][ring]
				if segData["type"] == "DEFAULT":
					pass
					apothem = self.ref_Octagon.apothem_ref + ring * (self.T + self.S)
					segPoly = self._octagon_ring_segment_polygon(apothem, self.T, segId)
					segLayer = segData["data"]["layer"]
					self._set_polygon_layer(segPoly, segLayer)
					self._append_gds_item(self.segment_gds_items, segPoly)
				elif segData["type"] == "BRIDGE":
					if self.Segments["config"]["bridge_extension_aligned"] == 1:
						maxJumps = max(list(map(abs, self._ccw_bridge_jumps(segId))))
						maxGap = maxJumps * (self.T + self.S)
						ccwGap = maxGap / 2.0
						cwGap = maxGap / 2.0
						ccwExt = 0
						cwExt = 0
					else:
						ccw_extensions = self._determine_gaps_on_segment_group(segId, 0)
						cw_extensions = self._determine_gaps_on_segment_group(segId, 1)
						ccwGap = abs(self._ccw_bridge_jumps(segId)[ring]) * (self.T + self.S) / 2.0
						cwGap = abs(self._cw_bridge_jumps(segId)[ring]) * (self.T + self.S) / 2.0
						ccwExt = ccw_extensions[ring]
						cwExt = cw_extensions[ring]

					apothem = self.ref_Octagon.apothem_ref + ring * (self.T + self.S)
					segPoly = self._octagon_ring_with_asymmetrical_gap_polygon(apothem, self.T, segId, ccwGap + ccwExt,
					                                                           cwGap + cwExt)
					segLayer = segData["data"]["layer"]
					for s in segPoly:
						self._set_polygon_layer(s, segLayer)
						self._append_gds_item(self.segment_gds_items, s)

				elif segData["type"] == "PORT":
					pass
					arm_data = self.Arms[segData["data"]["arm"]]
					if arm_data["type"] == "SINGLE":
						pass
						apothem = self.ref_Octagon.apothem_ref + ring * (self.T + self.S)
						segPoly = self._octagon_ring_segment_polygon(apothem, self.T, segId)
						segLayer = segData["data"]["layer"]
						self._set_polygon_layer(segPoly, segLayer)
						self._append_gds_item(self.segment_gds_items, segPoly)
					elif arm_data["type"] == "DOUBLE":
						pass
						spacing = arm_data["spacing"]
						apothem = self.ref_Octagon.apothem_ref + ring * (self.T + self.S)
						segPoly = self._octagon_ring_with_asymmetrical_gap_polygon(apothem, self.T, segId,
						                                                           spacing / 2.0,
						                                                           spacing / 2.0)
						segLayer = segData["data"]["layer"]
						self._set_polygon_layer(segPoly, segLayer)
						self._append_gds_item(self.segment_gds_items, segPoly)

	def _set_polygon_layer(self, polygon, layerName):
		layer = self.Layers[layerName]
		gds_layer = layer["gds"]["layer"]
		gds_datatype = layer["gds"]["datatype"]

		if type(polygon).__name__ == "Polygon":
			polygon.gds_layer = gds_layer
			polygon.gds_datatype = gds_datatype
		elif type(polygon).__name__ == "list":
			for p in polygon:
				if type(p).__name__ == "Polygon":
					p.gds_layer = gds_layer
					p.gds_datatype = gds_datatype

	def _generate_bridge_items(self):
		pass
		config = self.Segments["config"]
		SegData = self.Segments["data"]

		for sgName, sgData in SegData.items():
			segId = sgData["id"]
			for ring in range(len(sgData["group"])):
				segData = sgData["group"][ring]
				if segData["type"] == "BRIDGE":
					pass
					angleDegree = segId * 45
					dx = self.ref_Octagon.apothem_ref + ring * (self.T + self.S)
					dy = abs(segData["data"]["jump"]) * (self.T + self.S)
					bridgePoly = None

					if segData["data"]["jump"] > 0:
						bridgePoly = Polygon(
							[
								Point(dx, -dy / 2.0),
								Point(dx + self.T, -dy / 2.0),
								Point(dx + self.T + dy, dy / 2.0),
								Point(dx + dy, dy / 2.0)
							]
						)
					elif segData["data"]["jump"] < 0:
						bridgePoly = Polygon(
							[
								Point(dx, -dy / 2.0),
								Point(dx + self.T, -dy / 2.0),
								Point(dx + self.T - dy, dy / 2.0),
								Point(dx - dy, dy / 2.0)
							]
						)

					center = Point(0, 0)
					bridgePoly.rotate_around(center, angleDegree)
					segLayer = self.Bridges[segData["data"]["bridge"]]["layer"]
					self._set_polygon_layer(bridgePoly, segLayer)
					self._append_gds_item(self.bridge_gds_items, bridgePoly)

	def _generate_bridge_extensions_items(self):
		pass
		config = self.Segments["config"]
		SegData = self.Segments["data"]

		for sgName, sgData in SegData.items():
			segId = sgData["id"]
			angleDegree = segId * 45
			for ring in range(len(sgData["group"])):
				segData = sgData["group"][ring]
				if segData["type"] == "BRIDGE":
					dx = self.ref_Octagon.apothem_ref + ring * (self.T + self.S)
					ccwGap, cwGap, ccwExt, cwExt = self._get_gap_and_extension_info(segId, ring)

					if ccwExt > 0:
						extensionPolyCCW = Polygon(
							[
								Point(dx, -ccwGap),
								Point(dx + self.T, -ccwGap),
								Point(dx + self.T, -ccwGap - ccwExt),
								Point(dx, -ccwGap - ccwExt)
							]
						)
						extensionPolyCCW.rotate_around(Point(0, 0), angleDegree)
						segLayer = self.Bridges[segData["data"]["bridge"]]["layer"]
						self._set_polygon_layer(extensionPolyCCW, segLayer)
						self._append_gds_item(self.bridge_gds_items, extensionPolyCCW)

					if "ViaWidth" in self.Bridges[segData["data"]["bridge"]]:
						viaWidth = self.Bridges[segData["data"]["bridge"]]["ViaWidth"]
						viaPolyCCW = Polygon(
							[
								Point(dx, -ccwGap - ccwExt),
								Point(dx + self.T, -ccwGap - ccwExt),
								Point(dx + self.T, -ccwGap - ccwExt - viaWidth),
								Point(dx, -ccwGap - ccwExt - viaWidth)
							]
						)
						viaPolyCCW.rotate_around(Point(0, 0), angleDegree)


						self._generate_via_stack_on_polygon(viaPolyCCW,
						                              self.Bridges[segData["data"]["bridge"]]["ViaStackCCW"],
						                              0)

					cwRing = ring + self._ccw_bridge_jumps(segId)[ring]
					dx = self.ref_Octagon.apothem_ref + cwRing * (self.T + self.S)
					ccwGap, cwGap, ccwExt, cwExt = self._get_gap_and_extension_info(segId, cwRing)
					if cwExt > 0:
						extensionPolyCW = Polygon(
							[
								Point(dx, cwGap),
								Point(dx + self.T, cwGap),
								Point(dx + self.T, cwGap + cwExt),
								Point(dx, cwGap + cwExt)
							]
						)
						extensionPolyCW.rotate_around(Point(0, 0), angleDegree)
						segLayer = self.Bridges[segData["data"]["bridge"]]["layer"]
						self._set_polygon_layer(extensionPolyCW, segLayer)
						self._append_gds_item(self.bridge_gds_items, extensionPolyCW)

					if "ViaWidth" in self.Bridges[segData["data"]["bridge"]]:
						viaWidth = self.Bridges[segData["data"]["bridge"]]["ViaWidth"]
						viaPolyCW = Polygon(
							[
								Point(dx, cwGap + cwExt),
								Point(dx + self.T, cwGap + cwExt),
								Point(dx + self.T, cwGap + cwExt + viaWidth),
								Point(dx, cwGap + cwExt + viaWidth)
							]
						)
						viaPolyCW.rotate_around(Point(0, 0), angleDegree)

						self._generate_via_stack_on_polygon(viaPolyCW,
						                              self.Bridges[segData["data"]["bridge"]]["ViaStackCW"],
						                              0)

	def _generate_arm_items(self):
		pass
		config = self.Segments["config"]
		SegData = self.Segments["data"]

		for sgName, sgData in SegData.items():
			segId = sgData["id"]
			angleDegree = segId * 45
			for ring in range(len(sgData["group"])):
				segData = sgData["group"][ring]
				if segData["type"] == "PORT":
					armData = self.Arms[segData["data"]["arm"]]
					dxStart = self.ref_Octagon.apothem_ref + ring * (self.T + self.S) + self.T
					dxEnd = self.ref_Octagon.apothem_ref + self.N * self.T + (self.N - 1) * self.S + armData["length"]
					if armData["type"] == "SINGLE":
						armPoly = Polygon(
							[
								Point(dxStart, armData["width"] / 2.0),
								Point(dxEnd, armData["width"] / 2.0),
								Point(dxEnd, -armData["width"] / 2.0),
								Point(dxStart, -armData["width"] / 2.0)
							]
						)
						armPoly.rotate_around(Point(0, 0), angleDegree)
						armLayer = armData["layer"]
						self._set_polygon_layer(armPoly, armLayer)
						self._append_gds_item(self.arm_gds_items, armPoly)

						PortLine = copy.deepcopy(Line(Point(dxEnd, armData["width"] / 2.0), Point(dxEnd, -armData["width"] / 2.0)))
						PortLine.rotate_around(Point(0, 0), angleDegree)
						PortPoint = PortLine.midpoint()
						PortLayer = armData["layer"]
						Port = armData["port"]
						PortInfo = {"Line": PortLine, "Point": PortPoint, "Port": Port, "Layer": PortLayer}
						self.port_info.append(copy.deepcopy(PortInfo))

						if "viaStack" in armData:
							viaPoly = Polygon(
								(
									Point(dxStart, armData["width"] / 2.0),
									Point(dxStart - self.T, armData["width"] / 2.0),
									Point(dxStart - self.T, -armData["width"] / 2.0),
									Point(dxStart, -armData["width"] / 2.0)
								)
							)
							viaPoly.rotate_around(Point(0, 0), angleDegree)
							self._generate_via_stack_on_polygon(viaPoly, armData["viaStack"], 0)

					elif armData["type"] == "DOUBLE":
						dy = (armData["spacing"] + armData["width"]) / 2.0
						arm1Poly = Polygon(
							[
								Point(dxStart, dy + armData["width"] / 2.0),
								Point(dxEnd, dy + armData["width"] / 2.0),
								Point(dxEnd, dy - armData["width"] / 2.0),
								Point(dxStart, dy - armData["width"] / 2.0)
							]
						)
						arm1Poly.rotate_around(Point(0, 0), angleDegree)
						armLayer = armData["layer"]
						self._set_polygon_layer(arm1Poly, armLayer)
						self._append_gds_item(self.arm_gds_items, arm1Poly)

						if "viaStack" in armData:
							viaPoly = Polygon(
								(
									Point(dxStart, dy + armData["width"] / 2.0),
									Point(dxStart - self.T, dy + armData["width"] / 2.0),
									Point(dxStart - self.T, dy -armData["width"] / 2.0),
									Point(dxStart, dy +  -armData["width"] / 2.0)
								)
							)

							viaPoly.rotate_around(Point(0, 0), angleDegree)
							self._generate_via_stack_on_polygon(viaPoly, armData["viaStack"], 0)

						PortLine = copy.deepcopy(Line(Point(dxEnd, dy + armData["width"] / 2.0), Point(dxEnd, dy - armData["width"] / 2.0)))
						PortLine.rotate_around(Point(0, 0), angleDegree)
						PortPoint = PortLine.midpoint()
						PortLayer = armData["layer"]
						Port = armData["port"][0]
						PortInfo = {"Line": PortLine, "Point": PortPoint, "Port": Port, "Layer": PortLayer}
						self.port_info.append(copy.deepcopy(PortInfo))


						arm1Poly = Polygon(
							[
								Point(dxStart, -dy - armData["width"] / 2.0),
								Point(dxEnd, -dy - armData["width"] / 2.0),
								Point(dxEnd, -dy + armData["width"] / 2.0),
								Point(dxStart, -dy + armData["width"] / 2.0)
							]
						)
						arm1Poly.rotate_around(Point(0, 0), angleDegree)
						armLayer = armData["layer"]
						self._set_polygon_layer(arm1Poly, armLayer)
						self._append_gds_item(self.arm_gds_items, arm1Poly)


						if "viaStack" in armData:
							viaPoly = Polygon(
								(
									Point(dxStart, -dy + armData["width"] / 2.0),
									Point(dxStart - self.T, -dy + armData["width"] / 2.0),
									Point(dxStart - self.T, -dy -armData["width"] / 2.0),
									Point(dxStart, -dy +  -armData["width"] / 2.0)
								)
							)

							viaPoly.rotate_around(Point(0, 0), angleDegree)
							self._generate_via_stack_on_polygon(viaPoly, armData["viaStack"], 0)

						PortLine = copy.deepcopy(Line(Point(dxEnd, -dy - armData["width"] / 2.0), Point(dxEnd, -dy + armData["width"] / 2.0)))
						PortLine.rotate_around(Point(0, 0), angleDegree)
						PortPoint = PortLine.midpoint()
						PortLayer = armData["layer"]
						Port = armData["port"][1]
						PortInfo = {"Line": PortLine, "Point": PortPoint, "Port": Port, "Layer": PortLayer}
						self.port_info.append(copy.deepcopy(PortInfo))

	def _generate_guardRing_items(self):
		pass
		ref_apothem =  self.Parameters["apothem"] +   self.N * self.T +  (self.N- 1) * self.S +  self.GuardRing["data"]["distance"] 

		for guardRingItems in self.GuardRing["data"]["segments"]:
			if (self.GuardRing["data"]["segments"][guardRingItems]["shape"] == "hex"):
				offset = self.GuardRing["data"]["segments"][guardRingItems]["offset"]
				oct = Octagon(ref_apothem + offset)
				poly = Polygon(oct.vertices)
				layer = self.GuardRing["data"]["segments"][guardRingItems]["layer"]

				self._set_polygon_layer(poly, layer)
				self._append_gds_item(self.guard_ring_gds_items, poly)
			elif (self.GuardRing["data"]["segments"][guardRingItems]["shape"] == "hexRing"):
				offset = self.GuardRing["data"]["segments"][guardRingItems]["offset"]
				width = self.GuardRing["data"]["segments"][guardRingItems]["width"]

				if ("partialCut" in self.GuardRing["data"]["segments"][guardRingItems] and
						self.GuardRing["data"]["segments"][guardRingItems]["partialCut"]["use"]):
					for i in range(self.C):
						partialCutSegment = self.GuardRing["data"]["segments"][guardRingItems]["partialCut"][
							"segment"]
						if i == partialCutSegment:
							spacing = self.GuardRing["data"]["segments"][guardRingItems]["partialCut"][
								"spacing"]
							segments = self._octagon_ring_with_asymmetrical_gap_polygon(
								ref_apothem + offset, width, i, spacing / 2.0, spacing / 2.0)
							layer = self.GuardRing["data"]["segments"][guardRingItems]["layer"]

							self._set_polygon_layer(segments, layer)
							self._append_gds_item(self.guard_ring_gds_items, segments)

							if "contacts" in self.GuardRing["data"]["segments"][guardRingItems]:
								if self.GuardRing["data"]["segments"][guardRingItems]["contacts"][
									"use"]:
									viaStack = self.GuardRing["data"]["segments"][guardRingItems]["contacts"]["viaStack"]
									viaStackData = self.ViaPadStack[viaStack]
									viaMargin = viaStackData["margin"]
									self._generate_via_stack_on_polygon(segments[0], viaStack, viaMargin)
									self._generate_via_stack_on_polygon(segments[1], viaStack, viaMargin)

						else:
							spacing = self.GuardRing["data"]["segments"][guardRingItems]["partialCut"][
								"spacing"]
							segment = self._octagon_ring_segment_polygon(ref_apothem + offset, width, i)
							layer = self.GuardRing["data"]["segments"][guardRingItems]["layer"]
							self._set_polygon_layer(segment, layer)
							self._append_gds_item(self.guard_ring_gds_items, segment)

							if "contacts" in self.GuardRing["data"]["segments"][guardRingItems]:
								if self.GuardRing["data"]["segments"][guardRingItems]["contacts"][
									"use"]:
									viaStack = self.GuardRing["data"]["segments"][guardRingItems]["contacts"]["viaStack"]
									viaStackData = self.ViaPadStack[viaStack]
									viaMargin = viaStackData["margin"]
									self._generate_via_stack_on_polygon(segment, viaStack, viaMargin)

				else:
					for i in range(self.C):
						segment = self._octagon_ring_segment_polygon(ref_apothem + offset, width, i)
						layer = self.GuardRing["data"]["segments"][guardRingItems]["layer"]
						self._set_polygon_layer(segment, layer)
						self._append_gds_item(self.guard_ring_gds_items, segment)

						if "contacts" in self.GuardRing["data"]["segments"][guardRingItems]:
							if self.GuardRing["data"]["segments"][guardRingItems]["contacts"][
								"use"]:
								viaStack = self.GuardRing["data"]["segments"][guardRingItems]["contacts"]["viaStack"]
								viaStackData = self.ViaPadStack[viaStack]
								viaMargin = viaStackData["margin"]
								self._generate_via_stack_on_polygon(segment, viaStack, viaMargin)
								

	def _generate_dummy_fills(self):
		ref_apothem =  self.Parameters["apothem"] +   self.N * self.T +  (self.N- 1) * self.S +  self.GuardRing["data"]["distance"] 
		dummyFill = self.GuardRing["data"]["dummyFills"]
		if (dummyFill["type"] == "checkered"):
			groupSpacing = dummyFill["groupSpacing"]
			groupItems = []
			for itemsName, item in dummyFill["items"].items():
				if item["shape"] == "rect":
					dx = item["offsetX"]
					dy = item["offsetY"]
					length = item["length"]
					height = item["height"]

					rect = Polygon(
						[
							Point(dx - length / 2.0, dy - height / 2.0),
							Point(dx + length / 2.0, dy - height / 2.0),
							Point(dx + length / 2.0, dy + height / 2.0),
							Point(dx - length / 2.0, dy + height / 2.0),
						]
					)
					for layer in item["layers"]:
						r = rect.copy()
						self._set_polygon_layer(r, layer)
						groupItems.append(r)

			guardRingOctagon = Octagon(ref_apothem)

			for i in range(8):
				if i < 7:
					line = Line(guardRingOctagon.vertices[i], guardRingOctagon.vertices[i + 1])
				else:
					line = Line(guardRingOctagon.vertices[i], guardRingOctagon.vertices[0])
				self._fill_line_with_dummy_poly_group(groupItems, line, groupSpacing)


	def _generate_port_items(self):
		pass

		for p in self.port_info:
			#print(p)
			labelText = self.Ports[p["Port"]]["label"]
			position = p["Point"]
			gds_layer = self.Layers[p["Layer"]]["gds"]["layer"]
			gds_datatype = self.Layers[p["Layer"]]["gds"]["datatype"]
			label = gdspy.Label(labelText, (position.x, position.y), 'o', 0, 20, 0, gds_layer,gds_datatype)
			self.cell.add(label)


	def _fill_line_with_dummy_poly_group(self, dummyPolyGroup, line, groupSpacing, midSpacing=0):
		pass
		boundingBox = Polygon.bounding_box_polygons(dummyPolyGroup)
		groupLength = Line(boundingBox[0], boundingBox[1]).length()
		lineLength = line.length()
		noOfGroups = lineLength / (groupLength + groupSpacing)
		interval = lineLength / noOfGroups

		for i in range(-math.floor(noOfGroups / 2.0) + 1, math.floor(noOfGroups / 2.0)):
			x_offset = i * interval
			# print(x_offset)
			dummyPolyGroupInstance = Polygon.copy_polygons(dummyPolyGroup)
			Polygon.move_polygons_on_line(dummyPolyGroupInstance, Point(0, 0), line, x_offset, 0)
			for p in dummyPolyGroupInstance:
				if not self._polygon_is_near_or_intersecting(p, self.arm_gds_items, groupSpacing):
					self._append_gds_item(self.dummy_fills_gds_items, p)

	def _polygon_is_near_or_intersecting(self, polygon, otherPolygons, distanceThreshold=0):
		cnt = 0
		retVal = False
		for otherPolygon in otherPolygons:
			if polygon.gds_layer == otherPolygon.gds_layer and polygon.gds_datatype == otherPolygon.gds_datatype and (
					polygon._is_near_edge(otherPolygon, distanceThreshold) or polygon.is_inside(otherPolygon)):
				retVal = retVal or True
			else:
				retVal = retVal or False
		return retVal

	def _octagon_ring_segment_polygon(self, apothem, width, segment):

		inner_octagon_points = Octagon(apothem).vertices
		outer_octagon_points = Octagon(apothem + width).vertices

		if segment < 7:
			return Polygon([inner_octagon_points[segment], outer_octagon_points[segment],
			                outer_octagon_points[segment + 1], inner_octagon_points[segment + 1]])
		else:
			return Polygon([inner_octagon_points[segment], outer_octagon_points[segment], outer_octagon_points[0],
			                inner_octagon_points[0]])

	def _octagon_ring_with_asymmetrical_gap_polygon(self, apothem, width, segmentId, gapCCW=0, gapCW=0):

		segment_poly = self._octagon_ring_segment_polygon(apothem, width, segmentId)
		segment_midpoint = segment_poly.midpoint()

		# vertices of the segment polygon
		P0 = Point(segment_poly.vertices[0].x, segment_poly.vertices[0].y)
		P1 = Point(segment_poly.vertices[1].x, segment_poly.vertices[1].y)
		P2 = Point(segment_poly.vertices[3].x, segment_poly.vertices[3].y)
		P3 = Point(segment_poly.vertices[2].x, segment_poly.vertices[2].y)

		# The vertices of the gap
		G0 = Point(segment_midpoint.x + width / 2.0, segment_midpoint.y - gapCCW)
		G1 = Point(segment_midpoint.x - width / 2.0, segment_midpoint.y - gapCCW)
		G2 = Point(segment_midpoint.x + width / 2.0, segment_midpoint.y + gapCW)
		G3 = Point(segment_midpoint.x - width / 2.0, segment_midpoint.y + gapCW)

		# Rotating the vertices of the gap
		G0.rotate_around(segment_midpoint, segmentId * 45)
		G1.rotate_around(segment_midpoint, segmentId * 45)
		G2.rotate_around(segment_midpoint, segmentId * 45)
		G3.rotate_around(segment_midpoint, segmentId * 45)
		Poly1 = Polygon([G0, G1, P0, P1])
		Poly2 = Polygon([G2, G3, P2, P3])

		return [Poly1, Poly2]

	def _octagonal_ring_polygon(self, apothem, width):
		pass
		inner_octagon_points = Octagon(apothem)
		outer_octagon_points = Octagon(apothem + width)

		RingPoly = Polygon(
			[
				inner_octagon_points.vertices[0], inner_octagon_points.vertices[1], inner_octagon_points.vertices[2],
				inner_octagon_points.vertices[3],
				inner_octagon_points.vertices[4], inner_octagon_points.vertices[5], inner_octagon_points.vertices[6],
				inner_octagon_points.vertices[7],
				inner_octagon_points.vertices[0], outer_octagon_points.vertices[0], outer_octagon_points.vertices[7],
				outer_octagon_points.vertices[6],
				outer_octagon_points.vertices[5], outer_octagon_points.vertices[4], outer_octagon_points.vertices[3],
				outer_octagon_points.vertices[2],
				outer_octagon_points.vertices[1], outer_octagon_points.vertices[0]
			]
		)
		return RingPoly

	def _ccw_bridge_jumps(self, segment):
		ccw_bridge_jumps_array = []
		sg = self.Segments["data"]["S" + str(segment)]["group"]
		for j in range(len(self.Segments["data"]["S" + str(segment)]["group"])):
			if sg[j]["type"] == "BRIDGE":
				ccw_bridge_jumps_array.append(sg[j]["data"]["jump"])
			else:
				ccw_bridge_jumps_array.append(0)
		return ccw_bridge_jumps_array

	def _cw_bridge_jumps(self, segment):
		ccw_bridge_jumps_array = self._ccw_bridge_jumps(segment)
		cw_bridge_jumps_array = [0] * len(ccw_bridge_jumps_array)
		for i in range(len(ccw_bridge_jumps_array)):
			cw_bridge_jumps_array[i + ccw_bridge_jumps_array[i]] = -ccw_bridge_jumps_array[i]
		return cw_bridge_jumps_array

	def _get_gap_and_extension_info(self, segmentId, ring):
		if self.Segments["config"]["bridge_extension_aligned"] == 1:
			maxJumps = max(list(map(abs, self._ccw_bridge_jumps(segmentId))))
			maxGap = maxJumps * (self.T + self.S)
			ccwGap = abs(self._ccw_bridge_jumps(segmentId)[ring] * (self.T + self.S) / 2.0)
			cwGap = abs(self._cw_bridge_jumps(segmentId)[ring] * (self.T + self.S) / 2.0)
			ccwExt = (maxGap / 2.0 - ccwGap)
			cwExt = (maxGap / 2.0 - cwGap)
		else:
			ccwGap = abs(self._ccw_bridge_jumps(segmentId)[ring] * (self.T + self.S) / 2.0)
			cwGap = abs(self._cw_bridge_jumps(segmentId)[ring] * (self.T + self.S) / 2.0)
			ccwExt = abs(self._determine_gaps_on_segment_group(segmentId, 0)[ring])
			cwExt = abs(self._determine_gaps_on_segment_group(segmentId, 1)[ring])

		return ccwGap, cwGap, ccwExt, cwExt

	def _determine_gaps_on_segment_group(self, segment, ccwCw):
		# Contribution by Adrian Miguel Llop Recha,
		if ccwCw == 0:
			jumpArray = self._ccw_bridge_jumps(segment)
		else:
			jumpArray = self._cw_bridge_jumps(segment)
		absolute_jumpArray = list(map(abs, jumpArray))
		maxJump = max(absolute_jumpArray)
		extensions = []

		bb = [[0] * len(jumpArray) for i in range(len(jumpArray))]
		# print("id current\t id other \t delta ID \t box_current\t box_other\t deltaBox \t ccw_ext \t\tbb ")
		for id_current in range(len(jumpArray)):
			for id_other in range(len(jumpArray)):
				current_ext_unit = (maxJump - absolute_jumpArray[id_current])
				other_ext_unit = (maxJump - absolute_jumpArray[id_other])
				deltaId = abs(id_current - id_other)
				if current_ext_unit - other_ext_unit >= 0 and (id_current != id_other):
					ext = abs(current_ext_unit - other_ext_unit) - 2 * (deltaId - 1)
					if ext < 0:
						ext = 0
					if id_current - id_other < 0 and jumpArray[id_other] < 0:
						bb[id_current][id_other] = ext
					elif id_current - id_other > 0 and jumpArray[id_other] > 0:
						bb[id_current][id_other] = ext
					else:
						bb[id_current][id_other] = 0
				else:
					bb[id_current][id_other] = 0

		for i in range(7):
			x = (max(bb[i][0:])) * (self.T + self.S) / 2.0
			extensions.append(x)

		return extensions


	def _generate_via_stack_on_polygon(self, poly, ViaStack, margin=0):
		pass
		viaStackData = self.ViaPadStack[ViaStack]

		boundingBox = poly.bounding_box()
		boundingBoxPoly = Polygon(boundingBox)
		Bounding_box_bottom_left = boundingBoxPoly.vertices[0]
		Bounding_box_bottom_right = boundingBoxPoly.vertices[1]
		Bounding_box_top_left = boundingBoxPoly.vertices[3]
		Length_bounding_box = Bounding_box_bottom_left.distance(Bounding_box_bottom_right)
		Height_bounding_box = Bounding_box_bottom_left.distance(Bounding_box_top_left)
		topLayer = viaStackData["topLayer"]
		bottomLayer = viaStackData["bottomLayer"]
		gdsTopLayer = self.Layers[topLayer]["gds"]
		gdsBottomLayer = self.Layers[bottomLayer]["gds"]
		polyTop = poly.copy()
		polyBottom = poly.copy()
		polyTop.gds_layer = gdsTopLayer["layer"]
		polyTop.gds_datatype = gdsTopLayer["datatype"]
		polyBottom.gds_layer = gdsBottomLayer["layer"]
		polyBottom.gds_datatype = gdsBottomLayer["datatype"]

		self._append_gds_item(self.via_gds_items, polyTop)
		self._append_gds_item(self.via_gds_items, polyBottom)

		for vs in viaStackData["vias"]:
			ViaData = self.Via[vs]
			Via_L = ViaData["length"]
			Via_W = ViaData["width"]
			Via_S = ViaData["spacing"]
			Via_Layer = ViaData["layer"]
			Via_Angle = ViaData["angle"]
			dx = (Via_L + Via_S)
			dy = (Via_W + Via_S)
			c_max = ((Length_bounding_box - Via_S) / (Via_L + Via_S))
			r_max = ((Height_bounding_box - Via_S) / (Via_W + Via_S))

			for r in range(-round(r_max / 2) + 1, round(r_max / 2)):
				for c in range(-round(c_max / 2) + 1, round(c_max / 2)):
					x = poly.midpoint().x + dx * c
					y = poly.midpoint().y + dy * r
					viaMidPoint = Point(x, y)
					viaPoly = Polygon(
						[
							Point(x - Via_L / 2.0, y - Via_W / 2.0),
							Point(x + Via_L / 2.0, y - Via_W / 2.0),
							Point(x + Via_L / 2.0, y + Via_W / 2.0),
							Point(x - Via_L / 2.0, y + Via_W / 2.0),
						]
					)
					viaPoly.rotate_around(viaMidPoint, Via_Angle)
					if viaPoly.is_inside(poly) and not viaPoly._is_near_edge(poly, margin) and not viaPoly._is_near_edge(poly, Via_S):
						pass
						self._set_polygon_layer(viaPoly, Via_Layer)
						self._append_gds_item(self.via_gds_items, viaPoly)


	def _append_gds_item(self, item_list, poly):
		if type(poly).__name__ == "Polygon":
			item_list.append(poly)
		elif type(poly).__name__ == "list":
			for p in poly:
				if type(p).__name__ == "Polygon":
					item_list.append(p)
		else:
			pass

	def _draw_items_to_gds(self, item_list, sanpToGrid=True, gridPrecision=0.005, staircaseLines=False, staircasePrecision = 0.05):

		for p in item_list:
			poly = p

			if sanpToGrid == True:
				poly.snap_to_grid(gridPrecision)
			if staircaseLines == True:
				poly.generate_staircase_lines(staircasePrecision)

			self.cell.add(poly.to_gdspy_polygon(poly.gds_layer, poly.gds_datatype))
			pass



if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Your script description here")

    # Add command-line argument for JSON input (file or string)
    parser.add_argument("--artwork", "-a", required=True, help="JSON file path or JSON string")
    parser.add_argument("--output", "-o", help="Output path")
    parser.add_argument("--name", "-n", help="Output file name")

    args = parser.parse_args()

    # Check if the --artwork argument is provided
    if args.artwork:
        try:
            # Try to load the input as a JSON string
            artwork_json_input = json.loads(args.artwork)
        except json.JSONDecodeError:
            # If loading as JSON string fails, assume it's a file path and load the file
            try:
                with open(args.artwork, "r") as json_file:
                    artwork_json_input = json.load(json_file)
            except FileNotFoundError:
                print(f"Error: File '{args.artwork}' not found.")
                exit(1)
    else:
        print("Error: --artwork argument is required.")
        exit(1)

    inductive_component = inductiveComp(artwork_json_input, args.output, args.name)
	