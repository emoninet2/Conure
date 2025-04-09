import argparse
import copy
import json
import math
import os

import gdspy

from geometry.Line import Line
from geometry.Octagon import Octagon
from geometry.Point import Point
from geometry.Polygon import Polygon


class InductiveComp:
    """
    Class representing an inductive component for GDS layout generation.
    """

    def __init__(self, inductor_data, output_path=None, output_name=None, generate_svg=True):
        """
        Initialize the InductiveComp object.

        Parameters:
            inductor_data (dict): The inductor data loaded from JSON.
            output_path (str): The output directory path.
            output_name (str): The output file name.
            generate_svg (bool): Flag to generate SVG output. Defaults to True.
        """
        # Initialize parameters from the inductor data
        self.Metadata = inductor_data["metadata"]
        self.Parameters = inductor_data["parameters"]
        self.Segments = inductor_data["segments"]
        self.Bridges = inductor_data["bridges"]
        self.Arms = inductor_data["arms"]
        self.Ports = inductor_data["ports"]["data"]
        self.Via = inductor_data["via"]
        self.ViaPadStack = inductor_data["viaPadStack"]
        self.GuardRing = inductor_data["guardRing"]
        self.Layers = inductor_data["layer"]

        self.gridSize = 0.005
        self.T = self.Parameters["width"]   # Width of the conductors
        self.S = self.Parameters["spacing"]  # Spacing between the conductors
        self.C = self.Parameters["corners"]
        self.N = self.Parameters["rings"]
        self.ref_Octagon = Octagon(self.Parameters["apothem"])


        # Dynamically set parameters as attributes
        for key, value in self.Parameters.items():
            setattr(self, key, value)





        # Initialize GDS library and cell
        self.lib = gdspy.GdsLibrary()
        self.cell = self.lib.new_cell(self.Metadata["name"])

        # Initialize lists to store GDS items
        self.segment_gds_items = []
        self.bridge_gds_items = []
        self.arm_gds_items = []
        self.via_gds_items = []
        self.guard_ring_gds_items = []
        self.dummy_fills_gds_items = []
        self.port_gds_items = []
        self.port_info = []

        # Generate layout items
        self._generate_segment_items()
        self._generate_bridge_items()
        self._generate_bridge_extensions_items()
        self._generate_arm_items()
        self._generate_guard_ring_items()
        self._generate_dummy_fills()
        self._generate_port_items()

        # Draw items to GDS
        self._draw_items_to_gds(self.segment_gds_items, snap_to_grid=True, grid_precision=0.005)
        self._draw_items_to_gds(self.bridge_gds_items, snap_to_grid=True, grid_precision=0.005)
        self._draw_items_to_gds(self.arm_gds_items, snap_to_grid=True, grid_precision=0.005)
        self._draw_items_to_gds(self.via_gds_items, snap_to_grid=True, grid_precision=0.005)
        self._draw_items_to_gds(self.guard_ring_gds_items, snap_to_grid=True, grid_precision=0.005)
        self._draw_items_to_gds(
            self.dummy_fills_gds_items, snap_to_grid=True, grid_precision=0.005,
            staircase_lines=False, staircase_precision=0.02)

        # Set output path and name
        gds_output_path = output_path if output_path else self.Parameters["outputDir"]
        gds_output_name = output_name if output_name else self.Metadata["name"]

        # Create output directory if it doesn't exist
        if not os.path.exists(output_path):
            os.makedirs(output_path)

        # Write GDS and optionally SVG files
        self._write_output_files(output_path, output_name, generate_svg)


    # def _resolve_parameter(self, value):
    #     if isinstance(value, str):
    #         # If it's a string, use it as a key to fetch the value from self.Parameters.
    #         retVal = self.Parameters[value]
    #     else:
    #         # Otherwise, assume it's a numeric value and use it directly.
    #         retVal = value

    #     return retVal


    def _resolve_parameter(self, value):
        if isinstance(value, str):
            # Single string, fetch from Parameters
            return self.Parameters[value]
        elif isinstance(value, (list, tuple)):
            # Recursively resolve each element in the list or tuple
            return type(value)(self._resolve_parameter(v) for v in value)
        elif hasattr(value, '__array__'):  # catches numpy arrays
            import numpy as np
            return np.array([self._resolve_parameter(v) for v in value])
        else:
            # Numeric or directly usable value
            return value


    def _write_output_files(self, output_path, output_name, generate_svg):
        """
        Write the GDS and SVG output files.

        Parameters:
            output_path (str): The output directory path.
            output_name (str): The output file name.
            generate_svg (bool): Flag to generate SVG output.
        """
        gds_file = os.path.join(output_path, f"{output_name}.gds")
        self.lib.write_gds(gds_file)

        if generate_svg:
            svg_file = os.path.join(output_path, f"{output_name}.svg")
            self.cell.write_svg(svg_file)

    def _generate_segment_items(self):
        """
        Generate segment items based on the inductor data.
        """
        config = self.Segments["config"]
        seg_data = self.Segments["data"]

        for sg_name, sg_data in seg_data.items():
            seg_id = sg_data["id"]
            for ring in range(len(sg_data["group"])):
                seg_data_group = sg_data["group"][ring]
                if seg_data_group["type"] == "DEFAULT":
                    apothem = self.ref_Octagon.apothem_ref + ring * (self.T + self.S)
                    seg_poly = self._octagon_ring_segment_polygon(apothem, self.T, seg_id)
                    seg_layer = seg_data_group["data"]["layer"]
                    self._set_polygon_layer(seg_poly, seg_layer)
                    self._append_gds_item(self.segment_gds_items, seg_poly)
                elif seg_data_group["type"] == "BRIDGE":
                    if self.Segments["config"]["bridge_extension_aligned"] == 1:
                        max_jumps = max(list(map(abs, self._ccw_bridge_jumps(seg_id))))
                        max_gap = max_jumps * (self.T + self.S)
                        ccw_gap = max_gap / 2.0
                        cw_gap = max_gap / 2.0
                        ccw_ext = 0
                        cw_ext = 0
                    else:
                        ccw_extensions = self._determine_gaps_on_segment_group(seg_id, 0)
                        cw_extensions = self._determine_gaps_on_segment_group(seg_id, 1)
                        ccw_gap = abs(self._ccw_bridge_jumps(seg_id)[ring]) * (self.T + self.S) / 2.0
                        cw_gap = abs(self._cw_bridge_jumps(seg_id)[ring]) * (self.T + self.S) / 2.0
                        ccw_ext = ccw_extensions[ring]
                        cw_ext = cw_extensions[ring]

                    apothem = self.ref_Octagon.apothem_ref + ring * (self.T + self.S)
                    seg_poly = self._octagon_ring_with_asymmetrical_gap_polygon(
                        apothem, self.T, seg_id, ccw_gap + ccw_ext, cw_gap + cw_ext)
                    seg_layer = seg_data_group["data"]["layer"]
                    for s in seg_poly:
                        self._set_polygon_layer(s, seg_layer)
                        self._append_gds_item(self.segment_gds_items, s)
                elif seg_data_group["type"] == "PORT":
                    arm_data = self.Arms[seg_data_group["data"]["arm"]]
                    if arm_data["type"] == "SINGLE":
                        apothem = self.ref_Octagon.apothem_ref + ring * (self.T + self.S)
                        seg_poly = self._octagon_ring_segment_polygon(apothem, self.T, seg_id)
                        seg_layer = seg_data_group["data"]["layer"]
                        self._set_polygon_layer(seg_poly, seg_layer)
                        self._append_gds_item(self.segment_gds_items, seg_poly)
                    elif arm_data["type"] == "DOUBLE":
                        #spacing = arm_data["spacing"]
                        spacing = self._resolve_parameter(arm_data["spacing"])
                        apothem = self.ref_Octagon.apothem_ref + ring * (self.T + self.S)
                        seg_poly = self._octagon_ring_with_asymmetrical_gap_polygon(
                            apothem, self.T, seg_id, spacing / 2.0, spacing / 2.0)
                        seg_layer = seg_data_group["data"]["layer"]
                        self._set_polygon_layer(seg_poly, seg_layer)
                        self._append_gds_item(self.segment_gds_items, seg_poly)

    def _set_polygon_layer(self, polygon, layer_name):
        """
        Set the GDS layer and datatype for a polygon.

        Parameters:
            polygon (Polygon or list): The polygon or list of polygons.
            layer_name (str): The name of the layer from the inductor data.
        """
        layer = self.Layers[layer_name]
        gds_layer = layer["gds"]["layer"]
        gds_datatype = layer["gds"]["datatype"]

        if isinstance(polygon, Polygon):
            polygon.gds_layer = gds_layer
            polygon.gds_datatype = gds_datatype
        elif isinstance(polygon, list):
            for p in polygon:
                if isinstance(p, Polygon):
                    p.gds_layer = gds_layer
                    p.gds_datatype = gds_datatype

    def _generate_bridge_items(self):
        """
        Generate bridge items based on the inductor data.
        """
        config = self.Segments["config"]
        seg_data = self.Segments["data"]

        for sg_name, sg_data in seg_data.items():
            seg_id = sg_data["id"]
            for ring in range(len(sg_data["group"])):
                seg_data_group = sg_data["group"][ring]
                if seg_data_group["type"] == "BRIDGE":
                    angle_degree = seg_id * 45
                    dx = self.ref_Octagon.apothem_ref + ring * (self.T + self.S)
                    dy = abs(seg_data_group["data"]["jump"]) * (self.T + self.S)
                    bridge_poly = None

                    if seg_data_group["data"]["jump"] > 0:
                        bridge_poly = Polygon([
                            Point(dx, -dy / 2.0),
                            Point(dx + self.T, -dy / 2.0),
                            Point(dx + self.T + dy, dy / 2.0),
                            Point(dx + dy, dy / 2.0)
                        ])
                    elif seg_data_group["data"]["jump"] < 0:
                        bridge_poly = Polygon([
                            Point(dx, -dy / 2.0),
                            Point(dx + self.T, -dy / 2.0),
                            Point(dx + self.T - dy, dy / 2.0),
                            Point(dx - dy, dy / 2.0)
                        ])

                    center = Point(0, 0)
                    bridge_poly.rotate_around(center, angle_degree)
                    seg_layer = self.Bridges[seg_data_group["data"]["bridge"]]["layer"]
                    self._set_polygon_layer(bridge_poly, seg_layer)
                    self._append_gds_item(self.bridge_gds_items, bridge_poly)

    def _generate_bridge_extensions_items(self):
        """
        Generate bridge extension items based on the inductor data.
        """
        config = self.Segments["config"]
        seg_data = self.Segments["data"]

        for sg_name, sg_data in seg_data.items():
            seg_id = sg_data["id"]
            angle_degree = seg_id * 45
            for ring in range(len(sg_data["group"])):
                seg_data_group = sg_data["group"][ring]
                if seg_data_group["type"] == "BRIDGE":
                    dx = self.ref_Octagon.apothem_ref + ring * (self.T + self.S)
                    ccw_gap, cw_gap, ccw_ext, cw_ext = self._get_gap_and_extension_info(seg_id, ring)

                    if ccw_ext > 0:
                        extension_poly_ccw = Polygon([
                            Point(dx, -ccw_gap),
                            Point(dx + self.T, -ccw_gap),
                            Point(dx + self.T, -ccw_gap - ccw_ext),
                            Point(dx, -ccw_gap - ccw_ext)
                        ])
                        extension_poly_ccw.rotate_around(Point(0, 0), angle_degree)
                        seg_layer = self.Bridges[seg_data_group["data"]["bridge"]]["layer"]
                        self._set_polygon_layer(extension_poly_ccw, seg_layer)
                        self._append_gds_item(self.bridge_gds_items, extension_poly_ccw)

                    if "ViaWidth" in self.Bridges[seg_data_group["data"]["bridge"]]:
                        via_width = self.Bridges[seg_data_group["data"]["bridge"]]["ViaWidth"]
                        via_poly_ccw = Polygon([
                            Point(dx, -ccw_gap - ccw_ext),
                            Point(dx + self.T, -ccw_gap - ccw_ext),
                            Point(dx + self.T, -ccw_gap - ccw_ext - via_width),
                            Point(dx, -ccw_gap - ccw_ext - via_width)
                        ])
                        via_poly_ccw.rotate_around(Point(0, 0), angle_degree)
                        self._generate_via_stack_on_polygon(
                            via_poly_ccw,
                            self.Bridges[seg_data_group["data"]["bridge"]]["ViaStackCCW"],
                            0)

                    cw_ring = ring + self._ccw_bridge_jumps(seg_id)[ring]
                    dx = self.ref_Octagon.apothem_ref + cw_ring * (self.T + self.S)
                    ccw_gap, cw_gap, ccw_ext, cw_ext = self._get_gap_and_extension_info(seg_id, cw_ring)
                    if cw_ext > 0:
                        extension_poly_cw = Polygon([
                            Point(dx, cw_gap),
                            Point(dx + self.T, cw_gap),
                            Point(dx + self.T, cw_gap + cw_ext),
                            Point(dx, cw_gap + cw_ext)
                        ])
                        extension_poly_cw.rotate_around(Point(0, 0), angle_degree)
                        seg_layer = self.Bridges[seg_data_group["data"]["bridge"]]["layer"]
                        self._set_polygon_layer(extension_poly_cw, seg_layer)
                        self._append_gds_item(self.bridge_gds_items, extension_poly_cw)

                    if "ViaWidth" in self.Bridges[seg_data_group["data"]["bridge"]]:
                        via_width = self.Bridges[seg_data_group["data"]["bridge"]]["ViaWidth"]
                        via_poly_cw = Polygon([
                            Point(dx, cw_gap + cw_ext),
                            Point(dx + self.T, cw_gap + cw_ext),
                            Point(dx + self.T, cw_gap + cw_ext + via_width),
                            Point(dx, cw_gap + cw_ext + via_width)
                        ])
                        via_poly_cw.rotate_around(Point(0, 0), angle_degree)
                        self._generate_via_stack_on_polygon(
                            via_poly_cw,
                            self.Bridges[seg_data_group["data"]["bridge"]]["ViaStackCW"],
                            0)




    def grid_adjusted_length(self,full_length, grid=0.005):
        """
        Adjusts the full length of a vertical line (from (0, -L) to (0, L)) so that when rotated by 45° about the origin,
        the endpoints snap exactly to a grid of given size (default is 0.005).

        Parameters:
            full_length (float): The original full length of the line. The half-length is full_length / 2.
            grid (float): The grid resolution (default: 0.005).

        Returns:
            new_full_length (float): The adjusted full length such that after a 45° rotation, the endpoints are on the grid.
            k (int): The grid multiple used in the conversion, which indicates that the half-length becomes k * (grid*sqrt(2)).
        """
        # Calculate the original half-length
        half_length = full_length / 2.0

        # Compute the grid step after rotation:
        grid_step_rotated = grid * math.sqrt(2)  # Because L_new / sqrt(2) = k * grid

        # Compute k (largest integer such that L_new <= original half_length)
        k = math.floor(half_length / grid_step_rotated)

        # New half-length that snaps to grid after rotation
        new_half_length = k * grid_step_rotated

        # New full length
        new_full_length = 2 * new_half_length

        return new_full_length, k



    def _generate_arm_items(self, maintain_shape_integrity= True):
        """
        Generate arm items based on the inductor data.
        """
        config = self.Segments["config"]
        seg_data = self.Segments["data"]

        for sg_name, sg_data in seg_data.items():
            seg_id = sg_data["id"]
            angle_degree = seg_id * 45
            for ring in range(len(sg_data["group"])):
                seg_data_group = sg_data["group"][ring]
                if seg_data_group["type"] == "PORT":

                    arm_data = self.Arms[seg_data_group["data"]["arm"]]


                    # arm_length_value = arm_data["length"]

                    # if isinstance(arm_length_value, str):
                    #     # If it's a string, use it as a key to fetch the value from self.Parameters.
                    #     arm_length = self.Parameters[arm_length_value]
                    # else:
                    #     # Otherwise, assume it's a numeric value and use it directly.
                    #     arm_length = arm_length_value


                    arm_length = self._resolve_parameter(arm_data["length"])
                    arm_width = self._resolve_parameter(arm_data["width"])
                    

                    dx_start = self.ref_Octagon.apothem_ref + ring * (self.T + self.S) + self.T
                    dx_end = (self.ref_Octagon.apothem_ref + self.N * self.T +
                              (self.N - 1) * self.S + arm_length)
                    
                    

                    if maintain_shape_integrity is True and angle_degree in [45, 135, 225, 315]:
                        grid_size = self.gridSize
                        arm_length, k_length = self.grid_adjusted_length(arm_length, grid_size)
                        arm_width, k_width = self.grid_adjusted_length(arm_width, grid_size)
                        dx_start_raw = dx_start
                        dx_end_raw = dx_end
                        dx_start,_ = self.grid_adjusted_length(dx_start, grid_size)
                        dx_end,_ = self.grid_adjusted_length(dx_end, grid_size)

                        dx_start = round(dx_start / grid_size) * grid_size
                        dx_end = round(dx_end / grid_size) * grid_size








                    if arm_data["type"] == "SINGLE":
         
                        arm_poly = Polygon([
                            Point(dx_start, arm_width / 2.0),
                            Point(dx_end, arm_width / 2.0),
                            Point(dx_end, -arm_width / 2.0),
                            Point(dx_start, -arm_width / 2.0)
                        ])



                        arm_poly.rotate_around(Point(0, 0), angle_degree)
                        arm_layer = arm_data["layer"]
                        self._set_polygon_layer(arm_poly, arm_layer)
                        self._append_gds_item(self.arm_gds_items, arm_poly)

                        port_line = copy.deepcopy(Line(
                            Point(dx_end, arm_width / 2.0),
                            Point(dx_end, -arm_width / 2.0)))
                        port_line.rotate_around(Point(0, 0), angle_degree)
                        port_point = port_line.midpoint()
                        port_layer = arm_data["layer"]
                        port = arm_data["port"]
                        port_info = {"Line": port_line, "Point": port_point,
                                     "Port": port, "Layer": port_layer}
                        self.port_info.append(copy.deepcopy(port_info))

                        if "viaStack" in arm_data:
                            via_poly = Polygon([
                                Point(dx_start, arm_width / 2.0),
                                Point(dx_start - self.T, arm_width / 2.0),
                                Point(dx_start - self.T, -arm_width / 2.0),
                                Point(dx_start, -arm_width/ 2.0)
                            ])
                            via_poly.rotate_around(Point(0, 0), angle_degree)
                            self._generate_via_stack_on_polygon(via_poly, arm_data["viaStack"], 0)
                    elif arm_data["type"] == "DOUBLE":

                        double_arm_spacing = self._resolve_parameter(arm_data["spacing"])
                        dy = (double_arm_spacing + arm_width) / 2.0
                        # First arm
                        arm1_poly = Polygon([
                            Point(dx_start, dy + arm_width / 2.0),
                            Point(dx_end, dy + arm_width / 2.0),
                            Point(dx_end, dy -arm_width / 2.0),
                            Point(dx_start, dy -arm_width / 2.0)
                        ])
                        arm1_poly.rotate_around(Point(0, 0), angle_degree)
                        arm_layer = arm_data["layer"]
                        self._set_polygon_layer(arm1_poly, arm_layer)
                        self._append_gds_item(self.arm_gds_items, arm1_poly)

                        if "viaStack" in arm_data:
                            via_poly = Polygon([
                                Point(dx_start, dy + arm_width / 2.0),
                                Point(dx_start - self.T, dy + arm_width / 2.0),
                                Point(dx_start - self.T, dy - arm_width / 2.0),
                                Point(dx_start, dy - arm_width / 2.0)
                            ])
                            via_poly.rotate_around(Point(0, 0), angle_degree)
                            self._generate_via_stack_on_polygon(via_poly, arm_data["viaStack"], 0)

                        port_line = copy.deepcopy(Line(
                            Point(dx_end, dy + arm_width / 2.0),
                            Point(dx_end, dy - arm_width / 2.0)))
                        port_line.rotate_around(Point(0, 0), angle_degree)
                        port_point = port_line.midpoint()
                        port_layer = arm_data["layer"]
                        port = arm_data["port"][0]
                        port_info = {"Line": port_line, "Point": port_point,
                                     "Port": port, "Layer": port_layer}
                        self.port_info.append(copy.deepcopy(port_info))

                        # Second arm
                        arm2_poly = Polygon([
                            Point(dx_start, -dy - arm_width / 2.0),
                            Point(dx_end, -dy - arm_width / 2.0),
                            Point(dx_end, -dy + arm_width / 2.0),
                            Point(dx_start, -dy + arm_width/ 2.0)
                        ])
                        arm2_poly.rotate_around(Point(0, 0), angle_degree)
                        self._set_polygon_layer(arm2_poly, arm_layer)
                        self._append_gds_item(self.arm_gds_items, arm2_poly)

                        if "viaStack" in arm_data:
                            via_poly = Polygon([
                                Point(dx_start, -dy + arm_width / 2.0),
                                Point(dx_start - self.T, -dy + arm_width/ 2.0),
                                Point(dx_start - self.T, -dy - arm_width / 2.0),
                                Point(dx_start, -dy - arm_width/ 2.0)
                            ])
                            via_poly.rotate_around(Point(0, 0), angle_degree)
                            self._generate_via_stack_on_polygon(via_poly, arm_data["viaStack"], 0)

                        port_line = copy.deepcopy(Line(
                            Point(dx_end, -dy - arm_width / 2.0),
                            Point(dx_end, -dy + arm_width / 2.0)))
                        port_line.rotate_around(Point(0, 0), angle_degree)
                        port_point = port_line.midpoint()
                        port_layer = arm_data["layer"]
                        port = arm_data["port"][1]
                        port_info = {"Line": port_line, "Point": port_point,
                                     "Port": port, "Layer": port_layer}
                        self.port_info.append(copy.deepcopy(port_info))

    def _generate_guard_ring_items(self):
        """
        Generate guard ring items based on the inductor data.
        """


        guardRingDistance = self._resolve_parameter(self.GuardRing["data"]["distance"])

        ref_apothem = (self.Parameters["apothem"] + self.N * self.T +
                       (self.N - 1) * self.S + guardRingDistance)

        for guard_ring_item in self.GuardRing["data"]["segments"]:
            segment = self.GuardRing["data"]["segments"][guard_ring_item]
            shape = segment["shape"]
            #offset = segment["offset"]
            offset = self._resolve_parameter(segment["offset"])

            layer = segment["layer"]

            if shape == "octagon":
                octagon = Octagon(ref_apothem + offset)
                poly = Polygon(octagon.vertices)
                self._set_polygon_layer(poly, layer)
                self._append_gds_item(self.guard_ring_gds_items, poly)
            elif shape == "octagonRing":
                width = segment["width"]
                if ("partialCut" in segment and segment["partialCut"]["use"]):

                    for i in range(self.C):

                        partialCutSegment = self._resolve_parameter(segment["partialCut"]["segment"])
                        partialCutSpacing = self._resolve_parameter(segment["partialCut"]["spacing"])


                        #print(partialCutSegment)

                        if isinstance(partialCutSegment, (list, tuple)) and i in partialCutSegment:
                            usePartialCutInSegment = True
                        elif partialCutSegment == i: 
                            usePartialCutInSegment = True
                        else:
                            usePartialCutInSegment = False



                        #if isinstance(partialCutSegment, (list, tuple)) and i in partialCutSegment:  
                        if usePartialCutInSegment == True:  
                            partial_cut_spacing = self._resolve_parameter(partialCutSpacing)
                            segments = self._octagon_ring_with_asymmetrical_gap_polygon(
                                ref_apothem + offset, width, i, partial_cut_spacing / 2.0, partial_cut_spacing / 2.0)
                            self._set_polygon_layer(segments, layer)
                            self._append_gds_item(self.guard_ring_gds_items, segments)

                            if "contacts" in segment and segment["contacts"]["use"]:
                                via_stack = segment["contacts"]["viaStack"]
                                via_stack_data = self.ViaPadStack[via_stack]

                                via_margin = self._resolve_parameter(via_stack_data["margin"])



                                self._generate_via_stack_on_polygon(
                                    segments[0], via_stack, via_margin)
                                self._generate_via_stack_on_polygon(
                                    segments[1], via_stack, via_margin)
                        else:
                            segment_poly = self._octagon_ring_segment_polygon(
                                ref_apothem + offset, width, i)
                            self._set_polygon_layer(segment_poly, layer)
                            self._append_gds_item(self.guard_ring_gds_items, segment_poly)

                            if "contacts" in segment and segment["contacts"]["use"]:
                                via_stack = segment["contacts"]["viaStack"]
                                via_stack_data = self.ViaPadStack[via_stack]
                                via_margin = self._resolve_parameter(via_stack_data["margin"])
                                self._generate_via_stack_on_polygon(
                                    segment_poly, via_stack, via_margin)
                else:
                    for i in range(self.C):
                        segment_poly = self._octagon_ring_segment_polygon(
                            ref_apothem + offset, width, i)
                        self._set_polygon_layer(segment_poly, layer)
                        self._append_gds_item(self.guard_ring_gds_items, segment_poly)

                        if "contacts" in segment and segment["contacts"]["use"]:
                            via_stack = segment["contacts"]["viaStack"]
                            via_stack_data = self.ViaPadStack[via_stack]
                            via_margin = self._resolve_parameter(via_stack_data["margin"])
                            self._generate_via_stack_on_polygon(
                                segment_poly, via_stack, via_margin)

    def _generate_dummy_fills(self):
        """
        Generate dummy fill items based on the inductor data.
        """
        guardRingDistance = self._resolve_parameter(self.GuardRing["data"]["distance"])

        ref_apothem = (self.Parameters["apothem"] + self.N * self.T +
                       (self.N - 1) * self.S + guardRingDistance)
        

        dummy_fill = self.GuardRing["data"]["dummyFills"]
        if dummy_fill["type"] == "checkered":
            group_spacing = self._resolve_parameter(dummy_fill["groupSpacing"])

            #group_spacing = dummy_fill["groupSpacing"]
            group_items = []
            group_items_grid_adjusted = []

            for item_name, item in dummy_fill["items"].items():
                if item["shape"] == "rect":
                    # dx = item["offsetX"]
                    # dy = item["offsetY"]
                    # length = item["length"]
                    # height = item["height"]

                    dx = self._resolve_parameter(item["offsetX"])
                    dy = self._resolve_parameter(item["offsetY"])
                    length = self._resolve_parameter(item["length"])
                    height = self._resolve_parameter(item["height"])

                    rect = Polygon([
                        Point(dx - length / 2.0, dy - height / 2.0),
                        Point(dx + length / 2.0, dy - height / 2.0),
                        Point(dx + length / 2.0, dy + height / 2.0),
                        Point(dx - length / 2.0, dy + height / 2.0),
                    ])

                    for layer in item["layers"]:
                        r = rect.copy()
                        self._set_polygon_layer(r, layer)
                        group_items.append(r)


                    length_grid_adjusted,_ = self.grid_adjusted_length(length, self.gridSize)
                    height_grid_adjusted,_ = self.grid_adjusted_length(height, self.gridSize)

                    rect_grid_adjusted = Polygon([
                        Point(dx - length_grid_adjusted / 2.0, dy - height_grid_adjusted / 2.0),
                        Point(dx + length_grid_adjusted / 2.0, dy - height_grid_adjusted / 2.0),
                        Point(dx + length_grid_adjusted / 2.0, dy + height_grid_adjusted / 2.0),
                        Point(dx - length_grid_adjusted / 2.0, dy + height_grid_adjusted / 2.0),
                    ])

                    for layer in item["layers"]:
                        r = rect_grid_adjusted.copy()
                        self._set_polygon_layer(r, layer)
                        group_items_grid_adjusted.append(r)

                

            guard_ring_octagon = Octagon(ref_apothem)
            for i in range(8):
                line = None
                if i < 7:
                    line = Line(guard_ring_octagon.vertices[i], guard_ring_octagon.vertices[i + 1])
                else:
                    line = Line(guard_ring_octagon.vertices[i], guard_ring_octagon.vertices[0])

                if i%2 == 0:
                    self._fill_line_with_dummy_poly_group(group_items, line, group_spacing)
                else:
                    self._fill_line_with_dummy_poly_group(group_items_grid_adjusted, line, group_spacing)




    def _generate_port_items(self):
        """
        Generate port items based on the inductor data.
        """
        for p in self.port_info:
            label_text = self.Ports[p["Port"]]["label"]
            position = p["Point"]
            gds_layer = self.Layers[p["Layer"]]["gds"]["layer"]
            gds_datatype = self.Layers[p["Layer"]]["gds"]["datatype"]
            label = gdspy.Label(
                label_text, (position.x, position.y), 'o', 0, 20, 0, gds_layer, gds_datatype)
            self.cell.add(label)

    def _fill_line_with_dummy_poly_group(self, dummy_poly_group, line, group_spacing, mid_spacing=0):
        """
        Fill a line with a group of dummy polygons.

        Parameters:
            dummy_poly_group (list): List of polygons representing the dummy fill group.
            line (Line): The line along which to place the dummy fills.
            group_spacing (float): The spacing between dummy fill groups.
            mid_spacing (float): The spacing within a dummy fill group.
        """
        bounding_box = Polygon.bounding_box_polygons(dummy_poly_group)
        group_length = Line(bounding_box[0], bounding_box[1]).length()
        line_length = line.length()
        no_of_groups = line_length / (group_length + group_spacing)
        interval = line_length / no_of_groups

        for i in range(-math.floor(no_of_groups / 2.0) + 1, math.floor(no_of_groups / 2.0)):
            x_offset = i * interval
            dummy_poly_group_instance = Polygon.copy_polygons(dummy_poly_group)
            Polygon.move_polygons_on_line(
                dummy_poly_group_instance, Point(0, 0), line, x_offset, 0)
            for p in dummy_poly_group_instance:
                if not self._polygon_is_near_or_intersecting(p, self.arm_gds_items, group_spacing):
                    self._append_gds_item(self.dummy_fills_gds_items, p)

    def _polygon_is_near_or_intersecting(self, polygon, other_polygons, distance_threshold=0):
        """
        Check if a polygon is near or intersecting with other polygons.

        Parameters:
            polygon (Polygon): The polygon to check.
            other_polygons (list): List of other polygons to compare against.
            distance_threshold (float): The distance threshold for "nearness".

        Returns:
            bool: True if near or intersecting, False otherwise.
        """
        ret_val = False
        for other_polygon in other_polygons:
            if (polygon.gds_layer == other_polygon.gds_layer and
                    polygon.gds_datatype == other_polygon.gds_datatype and
                    (polygon._is_near_edge(other_polygon, distance_threshold) or
                     polygon.is_inside(other_polygon))):
                ret_val = True
                break
        return ret_val

    def _octagon_ring_segment_polygon(self, apothem, width, segment):
        """
        Create a polygon representing a segment of an octagonal ring.

        Parameters:
            apothem (float): The apothem of the inner octagon.
            width (float): The width of the ring.
            segment (int): The segment index (0-7).

        Returns:
            Polygon: The polygon representing the segment.
        """
        inner_octagon_points = Octagon(apothem).vertices
        outer_octagon_points = Octagon(apothem + width).vertices

        if segment < 7:
            return Polygon([inner_octagon_points[segment], outer_octagon_points[segment],
                            outer_octagon_points[segment + 1], inner_octagon_points[segment + 1]])
        else:
            return Polygon([inner_octagon_points[segment], outer_octagon_points[segment], outer_octagon_points[0],
                            inner_octagon_points[0]])

    def _octagon_ring_with_asymmetrical_gap_polygon(self, apothem, width, segment_id, gap_ccw=0, gap_cw=0):
        """
        Create polygons representing a segment of an octagonal ring with asymmetrical gaps.

        Parameters:
            apothem (float): The apothem of the inner octagon.
            width (float): The width of the ring.
            segment_id (int): The segment index (0-7).
            gap_ccw (float): The gap size in the counter-clockwise direction.
            gap_cw (float): The gap size in the clockwise direction.

        Returns:
            list: A list of two polygons representing the segmented ring.
        """
        segment_poly = self._octagon_ring_segment_polygon(apothem, width, segment_id)
        segment_midpoint = segment_poly.midpoint()

        # Vertices of the segment polygon
        P0 = segment_poly.vertices[0]
        P1 = segment_poly.vertices[1]
        P2 = segment_poly.vertices[3]
        P3 = segment_poly.vertices[2]

        # The vertices of the gap
        G0 = Point(segment_midpoint.x + width / 2.0, segment_midpoint.y - gap_ccw)
        G1 = Point(segment_midpoint.x - width / 2.0, segment_midpoint.y - gap_ccw)
        G2 = Point(segment_midpoint.x + width / 2.0, segment_midpoint.y + gap_cw)
        G3 = Point(segment_midpoint.x - width / 2.0, segment_midpoint.y + gap_cw)

        # Rotating the vertices of the gap
        G0.rotate_around(segment_midpoint, segment_id * 45)
        G1.rotate_around(segment_midpoint, segment_id * 45)
        G2.rotate_around(segment_midpoint, segment_id * 45)
        G3.rotate_around(segment_midpoint, segment_id * 45)

        poly1 = Polygon([G0, G1, P0, P1])
        poly2 = Polygon([G2, G3, P2, P3])

        return [poly1, poly2]

    def _ccw_bridge_jumps(self, segment):
        """
        Compute the counter-clockwise bridge jumps for a given segment.

        Parameters:
            segment (int): The segment index.

        Returns:
            list: A list of bridge jumps for each ring in the segment.
        """
        ccw_bridge_jumps_array = []
        sg = self.Segments["data"]["S" + str(segment)]["group"]
        for j in range(len(sg)):
            if sg[j]["type"] == "BRIDGE":
                ccw_bridge_jumps_array.append(sg[j]["data"]["jump"])
            else:
                ccw_bridge_jumps_array.append(0)
        return ccw_bridge_jumps_array

    def _cw_bridge_jumps(self, segment):
        """
        Compute the clockwise bridge jumps for a given segment.

        Parameters:
            segment (int): The segment index.

        Returns:
            list: A list of bridge jumps for each ring in the segment.
        """
        ccw_bridge_jumps_array = self._ccw_bridge_jumps(segment)
        cw_bridge_jumps_array = [0] * len(ccw_bridge_jumps_array)
        for i in range(len(ccw_bridge_jumps_array)):
            if i + ccw_bridge_jumps_array[i] < len(cw_bridge_jumps_array):
                cw_bridge_jumps_array[i + ccw_bridge_jumps_array[i]] = -ccw_bridge_jumps_array[i]
        return cw_bridge_jumps_array

    def _get_gap_and_extension_info(self, segment_id, ring):
        """
        Get gap and extension information for a given segment and ring.

        Parameters:
            segment_id (int): The segment index.
            ring (int): The ring index.

        Returns:
            tuple: (ccw_gap, cw_gap, ccw_ext, cw_ext)
        """
        if self.Segments["config"]["bridge_extension_aligned"] == 1:
            max_jumps = max(list(map(abs, self._ccw_bridge_jumps(segment_id))))
            max_gap = max_jumps * (self.T + self.S)
            ccw_gap = abs(self._ccw_bridge_jumps(segment_id)[ring] * (self.T + self.S) / 2.0)
            cw_gap = abs(self._cw_bridge_jumps(segment_id)[ring] * (self.T + self.S) / 2.0)
            ccw_ext = (max_gap / 2.0 - ccw_gap)
            cw_ext = (max_gap / 2.0 - cw_gap)
        else:
            ccw_gap = abs(self._ccw_bridge_jumps(segment_id)[ring] * (self.T + self.S) / 2.0)
            cw_gap = abs(self._cw_bridge_jumps(segment_id)[ring] * (self.T + self.S) / 2.0)
            ccw_ext = abs(self._determine_gaps_on_segment_group(segment_id, 0)[ring])
            cw_ext = abs(self._determine_gaps_on_segment_group(segment_id, 1)[ring])

        return ccw_gap, cw_gap, ccw_ext, cw_ext

    def _determine_gaps_on_segment_group(self, segment, ccw_cw):
        """
        Determine the gaps on a segment group.

        Parameters:
            segment (int): The segment index.
            ccw_cw (int): 0 for CCW, 1 for CW.

        Returns:
            list: A list of extensions for each ring.
        """
        if ccw_cw == 0:
            jump_array = self._ccw_bridge_jumps(segment)
        else:
            jump_array = self._cw_bridge_jumps(segment)
        absolute_jump_array = list(map(abs, jump_array))
        max_jump = max(absolute_jump_array)
        extensions = []

        bb = [[0] * len(jump_array) for _ in range(len(jump_array))]
        for id_current in range(len(jump_array)):
            for id_other in range(len(jump_array)):
                current_ext_unit = (max_jump - absolute_jump_array[id_current])
                other_ext_unit = (max_jump - absolute_jump_array[id_other])
                delta_id = abs(id_current - id_other)
                if current_ext_unit - other_ext_unit >= 0 and (id_current != id_other):
                    ext = abs(current_ext_unit - other_ext_unit) - 2 * (delta_id - 1)
                    if ext < 0:
                        ext = 0
                    if id_current - id_other < 0 and jump_array[id_other] < 0:
                        bb[id_current][id_other] = ext
                    elif id_current - id_other > 0 and jump_array[id_other] > 0:
                        bb[id_current][id_other] = ext
                    else:
                        bb[id_current][id_other] = 0
                else:
                    bb[id_current][id_other] = 0

        for i in range(len(jump_array)):
            x = (max(bb[i][0:])) * (self.T + self.S) / 2.0
            extensions.append(x)

        return extensions

    def _generate_via_stack_on_polygon(self, poly, via_stack, margin=0):
        """
        Generate a via stack on a given polygon.

        Parameters:
            poly (Polygon): The polygon to place the via stack on.
            via_stack (str): The name of the via stack from the inductor data.
            margin (float): Margin to keep from the polygon edges.
        """
        via_stack_data = self.ViaPadStack[via_stack]

        bounding_box = poly.bounding_box()
        bounding_box_poly = Polygon(bounding_box)
        length_bounding_box = Line(bounding_box_poly.vertices[0], bounding_box_poly.vertices[1]).length()
        height_bounding_box = Line(bounding_box_poly.vertices[0], bounding_box_poly.vertices[3]).length()

        top_layer = via_stack_data["topLayer"]
        bottom_layer = via_stack_data["bottomLayer"]
        gds_top_layer = self.Layers[top_layer]["gds"]
        gds_bottom_layer = self.Layers[bottom_layer]["gds"]
        poly_top = poly.copy()
        poly_bottom = poly.copy()
        poly_top.gds_layer = gds_top_layer["layer"]
        poly_top.gds_datatype = gds_top_layer["datatype"]
        poly_bottom.gds_layer = gds_bottom_layer["layer"]
        poly_bottom.gds_datatype = gds_bottom_layer["datatype"]

        self._append_gds_item(self.via_gds_items, poly_top)
        self._append_gds_item(self.via_gds_items, poly_bottom)

        for vs in via_stack_data["vias"]:
            via_data = self.Via[vs]
            via_layer = via_data["layer"]


            via_l = self._resolve_parameter(via_data["length"])
            via_w = self._resolve_parameter(via_data["width"])
            via_s = self._resolve_parameter(via_data["spacing"])
            via_angle = self._resolve_parameter(via_data["angle"])


            dx = (via_l + via_s)
            dy = (via_w + via_s)
            c_max = ((length_bounding_box - via_s) / (via_l + via_s))
            r_max = ((height_bounding_box - via_s) / (via_w + via_s))

            for r in range(-round(r_max / 2) + 1, round(r_max / 2)):
                for c in range(-round(c_max / 2) + 1, round(c_max / 2)):
                    x = poly.midpoint().x + dx * c
                    y = poly.midpoint().y + dy * r
                    via_midpoint = Point(x, y)
                    via_poly = Polygon([
                        Point(x - via_l / 2.0, y - via_w / 2.0),
                        Point(x + via_l / 2.0, y - via_w / 2.0),
                        Point(x + via_l / 2.0, y + via_w / 2.0),
                        Point(x - via_l / 2.0, y + via_w / 2.0),
                    ])
                    via_poly.rotate_around(via_midpoint, via_angle)
                    if (via_poly.is_inside(poly) and
                            not via_poly._is_near_edge(poly, margin) and
                            not via_poly._is_near_edge(poly, via_s)):
                        self._set_polygon_layer(via_poly, via_layer)
                        self._append_gds_item(self.via_gds_items, via_poly)

    def _append_gds_item(self, item_list, poly):
        """
        Append a polygon or list of polygons to a GDS item list.

        Parameters:
            item_list (list): The list to append to.
            poly (Polygon or list): The polygon or list of polygons to append.
        """
        if isinstance(poly, Polygon):
            item_list.append(poly)
        elif isinstance(poly, list):
            for p in poly:
                if isinstance(p, Polygon):
                    item_list.append(p)

    def _draw_items_to_gds(self, item_list, snap_to_grid=True, grid_precision=0.005,
                           staircase_lines=False, staircase_precision=0.05):
        """
        Draw items to the GDS cell.

        Parameters:
            item_list (list): The list of GDS items (polygons) to draw.
            snap_to_grid (bool): Flag to snap polygons to grid.
            grid_precision (float): The grid precision for snapping.
            staircase_lines (bool): Flag to generate staircase lines.
            staircase_precision (float): The precision for staircase lines.
        """
        for poly in item_list:
            if snap_to_grid:
                poly.snap_to_grid(grid_precision)
            if staircase_lines:
                poly.generate_staircase_lines(staircase_precision)
            self.cell.add(poly.to_gdspy_polygon(poly.gds_layer, poly.gds_datatype))


if __name__ == "__main__":
    # Parse command-line arguments
    parser = argparse.ArgumentParser(description="Inductive Component GDS Generator")
    parser.add_argument("--artwork", "-a", required=True,
                        help="JSON file path or JSON string")
    parser.add_argument("--output", "-o", help="Output path")
    parser.add_argument("--name", "-n", help="Output file name")
    parser.add_argument("--svg", action="store_true",
                        help="Enable generation of layout in SVG")
    args = parser.parse_args()

    # Load the artwork JSON input
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

    # Instantiate the InductiveComp object
    inductive_component = InductiveComp(
        artwork_json_input, args.output, args.name, args.svg)
