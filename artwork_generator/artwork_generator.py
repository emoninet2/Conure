#!/usr/bin/env python3
"""
Refactored Inductive Component GDS Generator

This module reads a JSON configuration to generate a GDS layout using gdspy.
It also optionally writes an SVG file representation.
"""

import argparse
import copy
import json
import math
import os
import logging
from typing import Any, Optional, Union, List, Tuple, Dict

import gdspy

# Geometry imports (assumed provided elsewhere in your project)
from geometry.Line import Line
from geometry.Octagon import Octagon
from geometry.Point import Point
from geometry.Polygon import Polygon


class ColorFormatter(logging.Formatter):
    COLORS = {
        logging.DEBUG: "\033[94m",     # Blue
        logging.INFO: "\033[92m",      # Green
        logging.WARNING: "\033[93m",   # Yellow
        logging.ERROR: "\033[91m",     # Red
        logging.CRITICAL: "\033[95m",  # Magenta
    }
    RESET = "\033[0m"

    def format(self, record):
        color = self.COLORS.get(record.levelno, self.RESET)
        timestamp = self.formatTime(record, self.datefmt)
        msg = super().format(record)
        return f"{timestamp} [ARTGEN] {color}{msg}{self.RESET}"



# Configure logging
logger = logging.getLogger()
logger.setLevel(logging.INFO)

if not logger.handlers:
    handler = logging.StreamHandler()
    handler.setFormatter(ColorFormatter('%(levelname)s - %(message)s'))
    logger.addHandler(handler)


# A safe environment for evaluating parameter expressions.
SAFE_EVAL_ENV: Dict[str, Any] = {
    **{k: getattr(math, k) for k in ['sqrt', 'log', 'sin', 'cos', 'tan', 'floor', 'ceil']},
    'abs': abs,
    'max': max,
    'min': min,
    'round': round,
}

# Constants for clarity
ROTATION_ANGLE_UNIT = 45  # Each segment corresponds to 45° rotation
DEFAULT_GRID_PRECISION = 0.005


class Component:
    """
    Class representing an inductive component for GDS layout generation.
    """

    def __init__(self, component_data: dict, output_path: Optional[str] = None,
                 output_name: Optional[str] = None, generate_layout: bool = True, generate_svg: bool = True) -> None:
        """
        Initialize the Component object.

        Parameters:
            component_data (dict): The component data loaded from JSON.
            output_path (str): The output directory path.
            output_name (str): The output file name.
            generate_svg (bool): Flag to generate SVG output. Defaults to True.
        """
        # Load metadata and parameters from component data
        self.Metadata: dict = component_data["metadata"]
        self.Parameters: dict = component_data["parameters"]

        # Resolve all parameters using the provided expressions.
        self.resolve_all_parameters()

        # Log the resolved parameters for debugging purposes.
        logging.debug("Resolved parameters: %s", self.Parameters)

        # Load layout definitions
        self.Segments: dict = component_data["segments"]
        self.Bridges: dict = component_data["bridges"]
        self.Arms: dict = component_data["arms"]
        self.Ports: dict = component_data["ports"]["data"]
        self.Via: dict = component_data["via"]
        self.ViaPadStack: dict = component_data["viaPadStack"]
        self.GuardRing: dict = component_data["guardRing"]
        self.Layers: dict = component_data["layer"]

        # Set key parameters.
        self.gridSize: float = self.Parameters["precision"]
        self.T: float = self.Parameters["width"]     # Width of the conductors
        self.S: float = self.Parameters["spacing"]     # Spacing between the conductors
        self.C: int = self.Parameters["corners"]
        self.N: int = self.Parameters["rings"]

        # Reference octagon for geometry calculations.
        self.ref_Octagon: Octagon = Octagon(self.Parameters["apothem"])

        # Dynamically assign all parameters as attributes.
        for key, value in self.Parameters.items():
            setattr(self, key, value)

        # Initialize GDS library and create the main cell.
        self.lib = gdspy.GdsLibrary()
        self.cell = self.lib.new_cell(self.Metadata["name"])

        # Initialize lists to store different GDS items.
        self.segment_gds_items: List[Polygon] = []
        self.bridge_gds_items: List[Polygon] = []
        self.arm_gds_items: List[Polygon] = []
        self.via_gds_items: List[Polygon] = []
        self.guard_ring_gds_items: List[Polygon] = []
        self.dummy_fills_gds_items: List[Polygon] = []
        self.port_gds_items: List[Any] = []
        self.port_info: List[dict] = []

        # Generate all layout items.
        self._generate_segment_items(snap_to_grid=True)
        self._generate_bridge_items(snap_to_grid=True)
        self._generate_bridge_extensions_items(snap_to_grid=True)
        self._generate_arm_items(snap_to_grid=True)
        self._generate_guard_ring_items(snap_to_grid=True)
        self._generate_dummy_fills(snap_to_grid=True)
        self._generate_port_items(snap_to_grid=True)

        # Draw the generated items to the GDS cell.
        self._draw_items_to_gds(self.segment_gds_items, snap_to_grid=True, grid_precision=DEFAULT_GRID_PRECISION)
        self._draw_items_to_gds(self.bridge_gds_items, snap_to_grid=True, grid_precision=DEFAULT_GRID_PRECISION)
        self._draw_items_to_gds(self.arm_gds_items, snap_to_grid=True, grid_precision=DEFAULT_GRID_PRECISION)
        self._draw_items_to_gds(self.via_gds_items, snap_to_grid=True, grid_precision=DEFAULT_GRID_PRECISION)
        self._draw_items_to_gds(self.guard_ring_gds_items, snap_to_grid=True, grid_precision=DEFAULT_GRID_PRECISION)
        self._draw_items_to_gds(
            self.dummy_fills_gds_items, snap_to_grid=True, grid_precision=DEFAULT_GRID_PRECISION,
            segmented_path=False, segmented_path_precision=0.02)

        # Define output paths and file names.
        out_path: str = output_path if output_path else self.Parameters["outputDir"]
        out_name: str = output_name if output_name else self.Metadata["name"]

        # Create the output directory if it doesn't exist.
        if not os.path.exists(out_path):
            os.makedirs(out_path)

        # Write GDS and optionally SVG files.
        self._write_output_files(out_path, out_name, generate_layout, generate_svg)

    def resolve_all_parameters(self) -> None:
        """
        Resolve all parameters defined in the Parameters dictionary.
        This method repeatedly attempts to evaluate each parameter based on already resolved values.
        """
        unresolved = dict(self.Parameters)
        resolved: dict = {}
        max_attempts = len(unresolved)

        for _ in range(max_attempts):
            for key in list(unresolved):
                try:
                    resolved[key] = self._resolve_parameter(unresolved[key], resolved)
                    del unresolved[key]
                except Exception:
                    # Retry later if dependent parameters are not yet resolved.
                    pass
            if not unresolved:
                break

        if unresolved:
            raise ValueError(f"Unresolved parameters after {max_attempts} attempts: {list(unresolved)}")

        self.Parameters = resolved

    def _resolve_parameter(self, value: Any, context: Optional[dict] = None) -> Any:
        """
        Resolve a single parameter value.

        Parameters:
            value (Any): The value to resolve.
            context (dict, optional): The context of already-resolved parameters.

        Returns:
            Any: The resolved value.
        """
        if context is None:
            context = self.Parameters  # fallback context

        if isinstance(value, str):
            try:
                return eval(value, SAFE_EVAL_ENV, context)
            except Exception:
                if value in context:
                    return self._resolve_parameter(context[value], context)
                else:
                    raise ValueError(f"Could not evaluate or resolve key: {value}")
        elif isinstance(value, (list, tuple)):
            return type(value)(self._resolve_parameter(v, context) for v in value)
        elif hasattr(value, '__array__'):
            import numpy as np
            return np.array([self._resolve_parameter(v, context) for v in value])
        else:
            return value

    def _write_output_files(self, output_path: str, output_name: str, generate_layout: bool, generate_svg: bool) -> None:
        """
        Write the GDS and SVG files if requested, and verify their existence before logging success.
        """
        if generate_layout:
            gds_file = os.path.join(output_path, f"{output_name}.gds")
            self.lib.write_gds(gds_file)
            if os.path.exists(gds_file):
                logging.info("GDS file written successfully: %s", gds_file)
            else:
                logging.error("Failed to write GDS file: %s", gds_file)

        if generate_svg:
            svg_file = os.path.join(output_path, f"{output_name}.svg")
            self.cell.write_svg(svg_file)
            if os.path.exists(svg_file):
                logging.info("SVG file written successfully: %s", svg_file)
            else:
                logging.error("Failed to write SVG file: %s", svg_file)


    def _append_gds_item(self, item_list: List[Polygon], poly: Union[Polygon, List[Polygon]]) -> None:
        """
        Append a polygon or list of polygons to a GDS item list.

        Parameters:
            item_list (list): The list to append to.
            poly (Polygon or list): The polygon(s) to append.
        """
        if isinstance(poly, Polygon):
            item_list.append(poly)
        elif isinstance(poly, list):
            for p in poly:
                if isinstance(p, Polygon):
                    item_list.append(p)

    def _draw_items_to_gds(self, item_list: List[Polygon], snap_to_grid: bool = True,
                           grid_precision: float = DEFAULT_GRID_PRECISION,
                           segmented_path: bool = False, segmented_path_precision: float = 0.05) -> None:
        """
        Draw items to the GDS cell.

        Parameters:
            item_list (list): List of polygons to draw.
            snap_to_grid (bool): Whether to snap the polygons to grid.
            grid_precision (float): The grid resolution.
            segmented_path (bool): Whether to generate segmented paths.
            segmented_path_precision (float): Precision for segmented path generation.
        """
        for poly in item_list:
            if snap_to_grid:
                poly.snap_to_grid(grid_precision)
            if segmented_path:
                poly.generate_segmented_path(segmented_path_precision)
            self.cell.add(poly.to_gdspy_polygon(poly.gds_layer, poly.gds_datatype))

    def grid_adjusted_length(self, full_length: float, grid: float = DEFAULT_GRID_PRECISION) -> Tuple[float, int]:
        """
        Adjust the length to snap endpoints to a grid after a 45° rotation.

        Parameters:
            full_length (float): The original full length.
            grid (float): The grid resolution.

        Returns:
            Tuple[float, int]: The new length and the grid multiple used.
        """
        half_length = full_length / 2.0
        grid_step_rotated = grid * math.sqrt(2)
        k = math.floor(half_length / grid_step_rotated)
        new_half_length = k * grid_step_rotated
        new_full_length = 2 * new_half_length
        return new_full_length, k

    # -------------------------------------------------------------------------
    # Item Generation Methods
    # -------------------------------------------------------------------------

    def _generate_segment_items(self, snap_to_grid: bool = True) -> None:
        """
        Generate segment items based on component data.
        """
        seg_config = self.Segments["config"]
        seg_data = self.Segments["data"]

        for seg_name, seg_def in seg_data.items():
            seg_id = seg_def["id"]
            for ring in range(len(seg_def["group"])):
                group_def = seg_def["group"][ring]
                # Compare type case insensitively
                if group_def["type"].lower() == "default":
                    apothem = self.ref_Octagon.apothem_ref + ring * (self.T + self.S)
                    seg_poly = self._octagon_ring_segment_polygon(apothem, self.T, seg_id)
                    seg_layer = group_def["data"]["layer"]
                    self._set_polygon_layer(seg_poly, seg_layer)
                    self._append_gds_item(self.segment_gds_items, seg_poly)
                elif group_def["type"].lower() == "bridge":
                    if self.Segments["config"].get("bridge_extension_aligned", 0) == 1:
                        max_jumps = max(abs(jump) for jump in self._ccw_bridge_jumps(seg_id))
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
                    seg_layer = group_def["data"]["layer"]
                    for poly in seg_poly:
                        self._set_polygon_layer(poly, seg_layer)
                        self._append_gds_item(self.segment_gds_items, poly)
                elif group_def["type"].lower() == "port":
                    arm_data = self.Arms[group_def["data"]["arm"]]
                    if arm_data["type"].lower() == "single":
                        apothem = self.ref_Octagon.apothem_ref + ring * (self.T + self.S)
                        seg_poly = self._octagon_ring_segment_polygon(apothem, self.T, seg_id)
                        seg_layer = group_def["data"]["layer"]
                        self._set_polygon_layer(seg_poly, seg_layer)
                        self._append_gds_item(self.segment_gds_items, seg_poly)
                    elif arm_data["type"].lower() == "double":
                        spacing = self._resolve_parameter(arm_data["spacing"])
                        apothem = self.ref_Octagon.apothem_ref + ring * (self.T + self.S)
                        seg_poly = self._octagon_ring_with_asymmetrical_gap_polygon(
                            apothem, self.T, seg_id, spacing / 2.0, spacing / 2.0)
                        seg_layer = group_def["data"]["layer"]
                        self._set_polygon_layer(seg_poly, seg_layer)
                        self._append_gds_item(self.segment_gds_items, seg_poly)

    def _set_polygon_layer(self, polygon: Union[Polygon, List[Polygon]], layer_name: str) -> None:
        """
        Set the GDS layer and datatype for a polygon (or list of polygons).

        Parameters:
            polygon (Polygon or list): The polygon(s) to adjust.
            layer_name (str): The target layer name.
        """
        layer = self.Layers[layer_name]
        #gds_layer = layer["gds"]["layer"]
        #gds_datatype = layer["gds"]["datatype"]

        gds_layer = self._resolve_parameter(layer["gds"]["layer"])
        gds_datatype = self._resolve_parameter(layer["gds"]["datatype"])

        if isinstance(polygon, Polygon):
            polygon.gds_layer = gds_layer
            polygon.gds_datatype = gds_datatype
        elif isinstance(polygon, list):
            for p in polygon:
                if isinstance(p, Polygon):
                    p.gds_layer = gds_layer
                    p.gds_datatype = gds_datatype

    def _generate_bridge_items(self, snap_to_grid: bool = True) -> None:
        """
        Generate bridge items based on the component data.
        """
        seg_data = self.Segments["data"]

        for seg_name, seg_def in seg_data.items():
            seg_id = seg_def["id"]
            for ring in range(len(seg_def["group"])):
                group_def = seg_def["group"][ring]
                if group_def["type"].lower() == "bridge":
                    angle_degree = seg_id * ROTATION_ANGLE_UNIT
                    dx = self.ref_Octagon.apothem_ref + ring * (self.T + self.S)
                    dy = abs(group_def["data"]["jump"]) * (self.T + self.S)
                    bridge_poly: Optional[Polygon] = None

                    if group_def["data"]["jump"] > 0:
                        bridge_poly = Polygon([
                            Point(dx, -dy / 2.0),
                            Point(dx + self.T, -dy / 2.0),
                            Point(dx + self.T + dy, dy / 2.0),
                            Point(dx + dy, dy / 2.0)
                        ])
                    elif group_def["data"]["jump"] < 0:
                        bridge_poly = Polygon([
                            Point(dx, -dy / 2.0),
                            Point(dx + self.T, -dy / 2.0),
                            Point(dx + self.T - dy, dy / 2.0),
                            Point(dx - dy, dy / 2.0)
                        ])

                    if bridge_poly is not None:
                        bridge_poly.rotate_around(Point(0, 0), angle_degree)
                        bridge_layer = self.Bridges[group_def["data"]["bridge"]]["layer"]
                        self._set_polygon_layer(bridge_poly, bridge_layer)
                        self._append_gds_item(self.bridge_gds_items, bridge_poly)

    def _generate_bridge_extensions_items(self, snap_to_grid: bool = True) -> None:
        """
        Generate bridge extension items.
        """
        seg_data = self.Segments["data"]

        for seg_name, seg_def in seg_data.items():
            seg_id = seg_def["id"]
            angle_degree = seg_id * ROTATION_ANGLE_UNIT
            for ring in range(len(seg_def["group"])):
                group_def = seg_def["group"][ring]
                if group_def["type"].lower() == "bridge":
                    dx = self.ref_Octagon.apothem_ref + ring * (self.T + self.S)
                    ccw_gap, cw_gap, ccw_ext, cw_ext = self._get_gap_and_extension_info(seg_id, ring)

                    # Handle CCW extension
                    if ccw_ext > 0:
                        extension_poly_ccw = Polygon([
                            Point(dx, -ccw_gap),
                            Point(dx + self.T, -ccw_gap),
                            Point(dx + self.T, -ccw_gap - ccw_ext),
                            Point(dx, -ccw_gap - ccw_ext)
                        ])
                        extension_poly_ccw.rotate_around(Point(0, 0), angle_degree)
                        bridge_layer = self.Bridges[group_def["data"]["bridge"]]["layer"]
                        self._set_polygon_layer(extension_poly_ccw, bridge_layer)
                        self._append_gds_item(self.bridge_gds_items, extension_poly_ccw)

                    # Generate via stack for CCW side if specified
                    if ("ViaWidth" in self.Bridges[group_def["data"]["bridge"]]
                            and self.Bridges[group_def["data"]["bridge"]]["ViaWidth"] is not None):
                        via_width = self.Bridges[group_def["data"]["bridge"]]["ViaWidth"]
                        via_poly_ccw = Polygon([
                            Point(dx, -ccw_gap - ccw_ext),
                            Point(dx + self.T, -ccw_gap - ccw_ext),
                            Point(dx + self.T, -ccw_gap - ccw_ext - via_width),
                            Point(dx, -ccw_gap - ccw_ext - via_width)
                        ])
                        via_poly_ccw.rotate_around(Point(0, 0), angle_degree)
                        self._generate_via_stack_on_polygon(
                            via_poly_ccw,
                            self.Bridges[group_def["data"]["bridge"]]["ViaStackCCW"],
                            0)

                    # Handle CW extension: adjust ring index by CW bridge jump.
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
                        bridge_layer = self.Bridges[group_def["data"]["bridge"]]["layer"]
                        self._set_polygon_layer(extension_poly_cw, bridge_layer)
                        self._append_gds_item(self.bridge_gds_items, extension_poly_cw)

                    if ("ViaWidth" in self.Bridges[group_def["data"]["bridge"]]
                            and self.Bridges[group_def["data"]["bridge"]]["ViaWidth"] is not None):
                        via_width = self.Bridges[group_def["data"]["bridge"]]["ViaWidth"]
                        via_poly_cw = Polygon([
                            Point(dx, cw_gap + cw_ext),
                            Point(dx + self.T, cw_gap + cw_ext),
                            Point(dx + self.T, cw_gap + cw_ext + via_width),
                            Point(dx, cw_gap + cw_ext + via_width)
                        ])
                        via_poly_cw.rotate_around(Point(0, 0), angle_degree)
                        self._generate_via_stack_on_polygon(
                            via_poly_cw,
                            self.Bridges[group_def["data"]["bridge"]]["ViaStackCW"],
                            0)

    def _generate_arm_items(self, snap_to_grid: bool = True) -> None:
        """
        Generate arm items based on the component data.
        """
        seg_data = self.Segments["data"]

        for seg_name, seg_def in seg_data.items():
            seg_id = seg_def["id"]
            angle_degree = seg_id * ROTATION_ANGLE_UNIT
            for ring in range(len(seg_def["group"])):
                group_def = seg_def["group"][ring]
                if group_def["type"].lower() == "port":
                    arm_data = self.Arms[group_def["data"]["arm"]]

                    # Resolve arm dimensions.
                    arm_length = self._resolve_parameter(arm_data["length"])
                    arm_width = self._resolve_parameter(arm_data["width"])
                    dx_start = (self.ref_Octagon.apothem_ref + ring * (self.T + self.S) + self.T)
                    dx_end = (self.ref_Octagon.apothem_ref + self.N * self.T +
                              (self.N - 1) * self.S + arm_length)

                    # Grid snapping adjustments for diagonal arms.
                    if snap_to_grid and angle_degree in [45, 135, 225, 315]:
                        grid_size = self.gridSize
                        arm_length, _ = self.grid_adjusted_length(arm_length, grid_size)
                        arm_width, _ = self.grid_adjusted_length(arm_width, grid_size)
                        dx_start, _ = self.grid_adjusted_length(dx_start, grid_size)
                        dx_end, _ = self.grid_adjusted_length(dx_end, grid_size)
                        dx_start = round(dx_start / grid_size) * grid_size
                        dx_end = round(dx_end / grid_size) * grid_size

                    if arm_data["type"].lower() == "single":
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

                        # Generate the port marker.
                        port_line = copy.deepcopy(Line(
                            Point(dx_end, arm_width / 2.0),
                            Point(dx_end, -arm_width / 2.0)))
                        port_line.rotate_around(Point(0, 0), angle_degree)
                        port_point = port_line.midpoint()
                        port = arm_data["port"]
                        port_info = {"Line": port_line, "Point": port_point,
                                     "Port": port, "Layer": arm_data["layer"]}
                        self.port_info.append(copy.deepcopy(port_info))

                        # Generate via stack if needed.
                        if "viaStack" in arm_data:
                            via_poly = Polygon([
                                Point(dx_start, arm_width / 2.0),
                                Point(dx_start - self.T, arm_width / 2.0),
                                Point(dx_start - self.T, -arm_width / 2.0),
                                Point(dx_start, -arm_width / 2.0)
                            ])
                            via_poly.rotate_around(Point(0, 0), angle_degree)
                            self._generate_via_stack_on_polygon(via_poly, arm_data["viaStack"], 0)

                    elif arm_data["type"].lower() == "double":
                        double_arm_spacing = self._resolve_parameter(arm_data["spacing"])
                        dy = (double_arm_spacing + arm_width) / 2.0
                        # First arm (upper)
                        arm1_poly = Polygon([
                            Point(dx_start, dy + arm_width / 2.0),
                            Point(dx_end, dy + arm_width / 2.0),
                            Point(dx_end, dy - arm_width / 2.0),
                            Point(dx_start, dy - arm_width / 2.0)
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
                        port = arm_data["port"][0]
                        port_info = {"Line": port_line, "Point": port_point,
                                     "Port": port, "Layer": arm_layer}
                        self.port_info.append(copy.deepcopy(port_info))

                        # Second arm (lower)
                        arm2_poly = Polygon([
                            Point(dx_start, -dy - arm_width / 2.0),
                            Point(dx_end, -dy - arm_width / 2.0),
                            Point(dx_end, -dy + arm_width / 2.0),
                            Point(dx_start, -dy + arm_width / 2.0)
                        ])
                        arm2_poly.rotate_around(Point(0, 0), angle_degree)
                        self._set_polygon_layer(arm2_poly, arm_layer)
                        self._append_gds_item(self.arm_gds_items, arm2_poly)

                        if "viaStack" in arm_data:
                            via_poly = Polygon([
                                Point(dx_start, -dy + arm_width / 2.0),
                                Point(dx_start - self.T, -dy + arm_width / 2.0),
                                Point(dx_start - self.T, -dy - arm_width / 2.0),
                                Point(dx_start, -dy - arm_width / 2.0)
                            ])
                            via_poly.rotate_around(Point(0, 0), angle_degree)
                            self._generate_via_stack_on_polygon(via_poly, arm_data["viaStack"], 0)

                        port_line = copy.deepcopy(Line(
                            Point(dx_end, -dy - arm_width / 2.0),
                            Point(dx_end, -dy + arm_width / 2.0)))
                        port_line.rotate_around(Point(0, 0), angle_degree)
                        port_point = port_line.midpoint()
                        port = arm_data["port"][1]
                        port_info = {"Line": port_line, "Point": port_point,
                                     "Port": port, "Layer": arm_layer}
                        self.port_info.append(copy.deepcopy(port_info))

    def _generate_guard_ring_items(self, snap_to_grid: bool = True) -> None:
        """
        Generate guard ring items based on the component data.
        """

        # Use case-insensitive check for useGuardRing
        if not self.GuardRing["config"].get("useGuardRing", False):
            logging.info("Guard Ring is disabled")
            return

        guardRingDistance = self._resolve_parameter(self.GuardRing["data"]["distance"])
        ref_apothem = (self.Parameters["apothem"] + self.N * self.T +
                       (self.N - 1) * self.S + guardRingDistance)

        for seg_key, segment in self.GuardRing["data"]["segments"].items():
            shape = segment["shape"]
            offset = self._resolve_parameter(segment["offset"])
            layer = segment["layer"]

            # Compare shape using lower-case
            if shape.lower() == "octagon":
                octagon = Octagon(ref_apothem + offset)
                poly = Polygon(octagon.vertices)
                self._set_polygon_layer(poly, layer)
                self._append_gds_item(self.guard_ring_gds_items, poly)
            elif shape.lower() == "octagonring":
                width = segment["width"]
                width = self._resolve_parameter(segment["width"])
                if ("partialCut" in segment and segment["partialCut"]["use"]):
                    for i in range(self.C):
                        partialCutSegment = self._resolve_parameter(segment["partialCut"]["segment"])
                        partialCutSpacing = self._resolve_parameter(segment["partialCut"]["spacing"])
                        # Determine if a partial cut is to be applied for this segment.
                        usePartialCutInSegment = (isinstance(partialCutSegment, (list, tuple)) and i in partialCutSegment) or (partialCutSegment == i)

                        if usePartialCutInSegment:
                            segments = self._octagon_ring_with_asymmetrical_gap_polygon(
                                ref_apothem + offset, width, i, partialCutSpacing / 2.0, partialCutSpacing / 2.0)
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

    def _generate_dummy_fills(self, snap_to_grid: bool = True) -> None:
        """
        Generate dummy fill items based on the component data.
        """

        if not self.GuardRing["config"].get("useGuardRing", False):
            logging.info("Guard Ring is disabled")
            return

        guardRingDistance = self._resolve_parameter(self.GuardRing["data"]["distance"])
        ref_apothem = (self.Parameters["apothem"] + self.N * self.T +
                       (self.N - 1) * self.S + guardRingDistance)
        dummy_fill = self.GuardRing["data"]["dummyFills"]

        if dummy_fill["type"].lower() == "checkered":
            group_spacing = self._resolve_parameter(dummy_fill["groupSpacing"])
            group_items: List[Polygon] = []
            group_items_grid_adjusted: List[Polygon] = []

            for item_name, item in dummy_fill["items"].items():
                if item["shape"].lower() == "rect":
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

                    length_grid_adjusted, _ = self.grid_adjusted_length(length, self.gridSize)
                    height_grid_adjusted, _ = self.grid_adjusted_length(height, self.gridSize)

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
            # Fill each edge of the octagon with dummy polygons
            for i in range(8):
                if i < 7:
                    line = Line(guard_ring_octagon.vertices[i], guard_ring_octagon.vertices[i + 1])
                else:
                    line = Line(guard_ring_octagon.vertices[i], guard_ring_octagon.vertices[0])
                if i % 2 == 0:
                    self._fill_line_with_dummy_poly_group(group_items, line, group_spacing)
                else:
                    self._fill_line_with_dummy_poly_group(group_items_grid_adjusted, line, group_spacing)

    def _fill_line_with_dummy_poly_group(self, dummy_poly_group: List[Polygon],
                                         line: Line, group_spacing: float, mid_spacing: float = 0) -> None:
        """
        Fill a line with a group of dummy polygons.

        Parameters:
            dummy_poly_group (list): List of dummy polygon prototypes.
            line (Line): The line on which to fill.
            group_spacing (float): Spacing between groups.
            mid_spacing (float): Intra-group spacing.
        """
        bounding_box = Polygon.bounding_box_polygons(dummy_poly_group)
        group_length = Line(bounding_box[0], bounding_box[1]).length()
        line_length = line.length()
        no_of_groups = line_length / (group_length + group_spacing)
        interval = line_length / no_of_groups

        for i in range(-math.floor(no_of_groups / 2.0) + 1, math.floor(no_of_groups / 2.0)):
            x_offset = i * interval
            dummy_poly_group_instance = Polygon.copy_polygons(dummy_poly_group)
            Polygon.move_polygons_on_line(dummy_poly_group_instance, Point(0, 0), line, x_offset, 0)
            for p in dummy_poly_group_instance:
                if not self._polygon_is_near_or_intersecting(p, self.arm_gds_items, group_spacing):
                    self._append_gds_item(self.dummy_fills_gds_items, p)

    def _polygon_is_near_or_intersecting(self, polygon: Polygon, other_polygons: List[Polygon],
                                           distance_threshold: float = 0) -> bool:
        """
        Check if a polygon is near or intersecting any polygon in a list.

        Parameters:
            polygon (Polygon): The polygon to check.
            other_polygons (list): The list of polygons to compare against.
            distance_threshold (float): The distance for "nearness."

        Returns:
            bool: True if near or intersecting, False otherwise.
        """
        for other_polygon in other_polygons:
            if (polygon.gds_layer == other_polygon.gds_layer and
                polygon.gds_datatype == other_polygon.gds_datatype and
                    (polygon._is_near_edge(other_polygon, distance_threshold) or polygon.is_inside(other_polygon))):
                return True
        return False

    def _generate_port_items(self, snap_to_grid: bool = True) -> None:
        """
        Generate port items for layout labeling.
        """
        for p in self.port_info:
            label_text = self.Ports[p["Port"]]["label"]
            position = p["Point"]
            gds_layer = self.Layers[p["Layer"]]["gds"]["layer"]
            gds_datatype = self.Layers[p["Layer"]]["gds"]["datatype"]
            # Removed unsupported x_offset parameter.
            label = gdspy.Label(
                label_text,
                (position.x, position.y),
                anchor='o',
                rotation=0,
                magnification=20,
                layer=gds_layer,
                texttype=gds_datatype)
            self.cell.add(label)

    def _octagon_ring_segment_polygon(self, apothem: float, width: float, segment: int) -> Polygon:
        """
        Create a polygon for a segment of an octagonal ring.

        Parameters:
            apothem (float): The inner octagon's apothem.
            width (float): The ring width.
            segment (int): The segment index (0-7).

        Returns:
            Polygon: The segment polygon.
        """
        inner_octagon_points = Octagon(apothem).vertices
        outer_octagon_points = Octagon(apothem + width).vertices

        if segment < 7:
            return Polygon([inner_octagon_points[segment], outer_octagon_points[segment],
                            outer_octagon_points[segment + 1], inner_octagon_points[segment + 1]])
        else:
            return Polygon([inner_octagon_points[segment], outer_octagon_points[segment],
                            outer_octagon_points[0], inner_octagon_points[0]])

    def _octagon_ring_with_asymmetrical_gap_polygon(self, apothem: float, width: float,
                                                    segment_id: int, gap_ccw: float, gap_cw: float) -> List[Polygon]:
        """
        Create polygons for an octagonal ring segment with asymmetrical gaps.

        Parameters:
            apothem (float): The inner octagon's apothem.
            width (float): The ring width.
            segment_id (int): The segment index (0-7).
            gap_ccw (float): Gap in the counter-clockwise direction.
            gap_cw (float): Gap in the clockwise direction.

        Returns:
            list: Two polygons representing the segmented ring.
        """
        segment_poly = self._octagon_ring_segment_polygon(apothem, width, segment_id)
        segment_midpoint = segment_poly.midpoint()

        # Define key vertices from the segment polygon.
        P0 = segment_poly.vertices[0]
        P1 = segment_poly.vertices[1]
        P2 = segment_poly.vertices[3]
        P3 = segment_poly.vertices[2]

        # Define gap vertices relative to the midpoint.
        G0 = Point(segment_midpoint.x + width / 2.0, segment_midpoint.y - gap_ccw)
        G1 = Point(segment_midpoint.x - width / 2.0, segment_midpoint.y - gap_ccw)
        G2 = Point(segment_midpoint.x + width / 2.0, segment_midpoint.y + gap_cw)
        G3 = Point(segment_midpoint.x - width / 2.0, segment_midpoint.y + gap_cw)

        # Rotate gap vertices around the segment midpoint.
        for pt in [G0, G1, G2, G3]:
            pt.rotate_around(segment_midpoint, segment_id * ROTATION_ANGLE_UNIT)

        poly1 = Polygon([G0, G1, P0, P1])
        poly2 = Polygon([G2, G3, P2, P3])
        return [poly1, poly2]

    def _ccw_bridge_jumps(self, segment: int) -> List[float]:
        """
        Compute counter-clockwise bridge jumps for a given segment.

        Parameters:
            segment (int): Segment index.

        Returns:
            list: List of bridge jumps per ring.
        """
        ccw_bridge_jumps_array = []
        group_data = self.Segments["data"]["S" + str(segment)]["group"]
        for item in group_data:
            if item["type"].lower() == "bridge":
                ccw_bridge_jumps_array.append(item["data"]["jump"])
            else:
                ccw_bridge_jumps_array.append(0)
        return ccw_bridge_jumps_array

    def _cw_bridge_jumps(self, segment: int) -> List[float]:
        """
        Compute clockwise bridge jumps based on counter-clockwise jumps.

        Parameters:
            segment (int): Segment index.

        Returns:
            list: List of clockwise bridge jumps per ring.
        """
        ccw_jumps = self._ccw_bridge_jumps(segment)
        cw_jumps = [0] * len(ccw_jumps)
        for i in range(len(ccw_jumps)):
            target_index = i + ccw_jumps[i]
            if target_index < len(cw_jumps):
                cw_jumps[target_index] = -ccw_jumps[i]
        return cw_jumps

    def _get_gap_and_extension_info(self, segment_id: int, ring: int) -> Tuple[float, float, float, float]:
        """
        Determine gap and extension values for a given segment and ring.

        Returns:
            Tuple containing (ccw_gap, cw_gap, ccw_ext, cw_ext).
        """
        if self.Segments["config"].get("bridge_extension_aligned", 0) == 1:
            max_jumps = max(abs(jump) for jump in self._ccw_bridge_jumps(segment_id))
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

    def _determine_gaps_on_segment_group(self, segment: int, ccw_cw: int) -> List[float]:
        """
        Calculate gap extensions for a segment group.

        Parameters:
            segment (int): Segment index.
            ccw_cw (int): 0 for CCW, 1 for CW.

        Returns:
            list: Extensions for each ring.
        """
        jump_array = self._ccw_bridge_jumps(segment) if ccw_cw == 0 else self._cw_bridge_jumps(segment)
        absolute_jumps = list(map(abs, jump_array))
        max_jump = max(absolute_jumps)
        extensions = []
        bb = [[0] * len(jump_array) for _ in range(len(jump_array))]

        for idx_current in range(len(jump_array)):
            for idx_other in range(len(jump_array)):
                current_ext_unit = max_jump - absolute_jumps[idx_current]
                other_ext_unit = max_jump - absolute_jumps[idx_other]
                delta_idx = abs(idx_current - idx_other)
                if current_ext_unit - other_ext_unit >= 0 and (idx_current != idx_other):
                    ext = abs(current_ext_unit - other_ext_unit) - 2 * (delta_idx - 1)
                    ext = ext if ext > 0 else 0
                    if (idx_current - idx_other < 0 and jump_array[idx_other] < 0) or \
                       (idx_current - idx_other > 0 and jump_array[idx_other] > 0):
                        bb[idx_current][idx_other] = ext
                    else:
                        bb[idx_current][idx_other] = 0
                else:
                    bb[idx_current][idx_other] = 0

        for i in range(len(jump_array)):
            extension_value = (max(bb[i][0:])) * (self.T + self.S) / 2.0
            extensions.append(extension_value)
        return extensions

    def _generate_via_stack_on_polygon(self, poly: Polygon, via_stack: str, margin: float = 0) -> None:
        """
        Generate via stacks (both top and bottom) on the provided polygon.

        Parameters:
            poly (Polygon): The base polygon.
            via_stack (str): Identifier for the via stack.
            margin (float): Margin required from the polygon edges.
        """
        via_stack_data = self.ViaPadStack[via_stack]
        bounding_box = poly.bounding_box()
        bounding_box_poly = Polygon(bounding_box)
        length_bb = Line(bounding_box_poly.vertices[0], bounding_box_poly.vertices[1]).length()
        height_bb = Line(bounding_box_poly.vertices[0], bounding_box_poly.vertices[3]).length()

        # Retrieve layer definitions for top and bottom vias.
        top_layer = via_stack_data["topLayer"]
        bottom_layer = via_stack_data["bottomLayer"]
        gds_top_layer = self.Layers[top_layer]["gds"]
        gds_bottom_layer = self.Layers[bottom_layer]["gds"]

        # Prepare copies of the polygon for top and bottom.
        poly_top = poly.copy()
        poly_bottom = poly.copy()
        poly_top.gds_layer = gds_top_layer["layer"]
        poly_top.gds_datatype = gds_top_layer["datatype"]
        poly_bottom.gds_layer = gds_bottom_layer["layer"]
        poly_bottom.gds_datatype = gds_bottom_layer["datatype"]

        self._append_gds_item(self.via_gds_items, poly_top)
        self._append_gds_item(self.via_gds_items, poly_bottom)

        # Process each via in the stack.
        for vs in via_stack_data["vias"]:
            via_data = self.Via[vs]
            via_layer = via_data["layer"]

            via_l = self._resolve_parameter(via_data["length"])
            via_w = self._resolve_parameter(via_data["width"])
            via_s = self._resolve_parameter(via_data["spacing"])
            via_angle = self._resolve_parameter(via_data["angle"])

            dx = via_l + via_s
            dy = via_w + via_s
            c_max = (length_bb - via_s) / (via_l + via_s)
            r_max = (height_bb - via_s) / (via_w + via_s)

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

# -------------------------------------------------------------------------
# End of item generation methods.
# -------------------------------------------------------------------------
if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Inductive Component GDS Generator")
    parser.add_argument("--artwork", "-a", required=True, help="JSON file path or JSON string")
    parser.add_argument("--output", "-o", help="Output path")
    parser.add_argument("--name", "-n", help="Output file name")
    parser.add_argument("--layout", action="store_true", help="Enable generation of layout in GDS")
    parser.add_argument("--svg", action="store_true", help="Enable generation of layout in SVG")
    parser.add_argument(
        "--log-level",
        choices=["debug", "info", "warning", "error", "critical"],
        help="Set the logging level"
    )
    parser.add_argument("--verbose", "-v", action="store_true", help="Enable verbose (debug) output")

    # ✅ Now parse all arguments
    args = parser.parse_args()

    # Set log level based on --log-level
    log_levels = {
        "debug": logging.DEBUG,
        "info": logging.INFO,
        "warning": logging.WARNING,
        "error": logging.ERROR,
        "critical": logging.CRITICAL
    }
    # Start with logging disabled
    logger.setLevel(logging.CRITICAL + 1)

    # If --log-level is provided
    if args.log_level:
        logger.setLevel(log_levels[args.log_level])

    # If --verbose is used, override
    if args.verbose:
        logger.setLevel(logging.DEBUG)

    # Load artwork JSON input.
    artwork_json_input: Any = None
    if args.artwork:
        try:
            artwork_json_input = json.loads(args.artwork)
        except json.JSONDecodeError:
            try:
                with open(args.artwork, "r") as json_file:
                    artwork_json_input = json.load(json_file)
            except FileNotFoundError:
                logging.error("Error: File '%s' not found.", args.artwork)
                exit(1)
    else:
        logging.error("Error: --artwork argument is required.")
        exit(1)

    try:
        inductive_component = Component(artwork_json_input, args.output, args.name, args.layout, args.svg)
        logging.info("Successfully generated artwork.")
    except Exception as e:
        logging.error("An error occurred during generation: %s", e)
        exit(1)
