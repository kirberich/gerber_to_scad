from pygerber.gerberx3.api.v2 import ParsedFile
from pygerber.gerberx3.parser2.commands2.arc2 import Arc2, CCArc2
from pygerber.gerberx3.parser2.commands2.flash2 import Flash2
from pygerber.gerberx3.parser2.commands2.line2 import Line2
from pygerber.gerberx3.parser2.commands2.region2 import Region2
from solid import (
    OpenSCADObject,
    linear_extrude,
    mirror,
    offset,
    polygon,
    rotate,
    scad_render,
    translate,
    union,
    utils,
)

from . import geometry
from .vector import V


class GerberConverter:
    """Converts parsed gerber outline and solderpaste files into an OpenSCAD stencil."""

    def __init__(
        self,
        *,
        outline_file: ParsedFile,
        solderpaste_file: ParsedFile,
        stencil_thickness: float = 0.2,
        include_ledge: bool = True,
        ledge_thickness: float = 1.2,
        full_ledge: bool = False,
        gap: float = 0,
        include_frame: bool = False,
        frame_width: float = 0,
        frame_height: float = 0,
        frame_thickness: float = 1.2,
        increase_hole_size_by: float = 0,
        flip_stencil: bool = False,
    ):
        self.outline_file = outline_file
        self.solderpaste_file = solderpaste_file
        self.stencil_thickness = stencil_thickness
        self.include_ledge = include_ledge
        self.ledge_thickness = ledge_thickness
        self.full_ledge = full_ledge
        self.gap = gap
        self.include_frame = include_frame
        self.frame_width = frame_width
        self.frame_height = frame_height
        self.frame_thickness = frame_thickness
        self.increase_hole_size_by = increase_hole_size_by
        self.flip_stencil = flip_stencil

    def convert(self) -> str:
        """Run the full conversion and return the OpenSCAD source."""
        outline_shape = self._outline_shape()
        cutout_polygon = self._create_cutouts()

        if self.gap:
            outline_shape = geometry.offset_shape(outline_shape, self.gap)

        # Move the polygons to be centered around the origin
        outline_polygon = polygon([v.as_tuple() for v in outline_shape])

        outline_bounds = geometry.bounding_box(outline_shape)
        outline_offset = outline_bounds[0] + (outline_bounds[2] - outline_bounds[0]) / 2
        centered_outline_polygon = translate(
            (-outline_offset[0], -outline_offset[1], 0)
        )(outline_polygon)
        cutout_polygon = translate((-outline_offset[0], -outline_offset[1], 0))(
            cutout_polygon
        )

        if self.flip_stencil:
            mirror_normal = (-1, 0, 0)
            centered_outline_polygon = mirror(mirror_normal)(centered_outline_polygon)
            cutout_polygon = mirror(mirror_normal)(cutout_polygon)

        stencil = linear_extrude(height=self.stencil_thickness)(
            centered_outline_polygon - cutout_polygon
        )

        if self.include_ledge:
            ledge_polygon = self._create_ledge(outline_shape)
            ledge = translate((-outline_offset[0], -outline_offset[1], 0))(
                utils.down(self.ledge_thickness - self.stencil_thickness)(
                    linear_extrude(height=self.ledge_thickness)(ledge_polygon)
                )
            )
            stencil = ledge + stencil

        elif self.include_frame:
            frame_shape = geometry.bounding_box(
                outline_shape, width=self.frame_width, height=self.frame_height
            )
            frame_polygon = (
                translate((-outline_offset[0], -outline_offset[1], 0))(
                    polygon([v.as_tuple() for v in frame_shape])
                )
                - centered_outline_polygon
            )
            frame = utils.down(self.frame_thickness - self.stencil_thickness)(
                linear_extrude(height=self.frame_thickness)(frame_polygon)
            )
            stencil = frame + stencil

        # Rotate the stencil to make it printable
        stencil = rotate(a=180, v=(1, 0, 0))(stencil)

        return scad_render(stencil)

    def _outline_shape(self) -> list[V]:
        """Extract board outline shape from the parsed outline gerber file.

        Returns the convex hull of all outline points.
        """
        points: list[V] = []

        for command in self.outline_file._command_buffer:  # pyright: ignore[reportPrivateUsage]
            if isinstance(command, Line2):
                points.extend(geometry.vertices_from_line_stroke(command))
            elif isinstance(command, (Arc2, CCArc2)):
                points.extend(geometry.vertices_from_arc(command))

        if not points:
            return self._outline_shape_from_bounds()

        return geometry.convex_hull(points)

    def _outline_shape_from_bounds(self) -> list[V]:
        """Fallback: create outline from file bounding box when no line/arc commands exist."""
        bbox = self.outline_file._command_buffer.get_bounding_box()  # pyright: ignore[reportPrivateUsage]
        return geometry.vertices_from_bounding_box(bbox)

    def _create_cutouts(self) -> OpenSCADObject:
        """Create cutout polygons from the parsed solderpaste gerber file."""
        polygons: list[OpenSCADObject] = []

        for command in self.solderpaste_file._command_buffer:  # pyright: ignore[reportPrivateUsage]
            if isinstance(command, Flash2):
                vertices = geometry.vertices_from_flash(command)
            elif isinstance(command, Line2):
                width = float(command.aperture.get_stroke_width().as_millimeters())
                if width > 0:
                    vertices = geometry.vertices_from_line_stroke(command)
                else:
                    continue
            elif isinstance(command, Region2):
                vertices = geometry.vertices_from_region(command)
            else:
                continue

            if len(vertices) < 3:
                continue

            shape_polygon = polygon([(v.x, v.y) for v in vertices])
            if self.increase_hole_size_by:
                shape_polygon = offset(delta=self.increase_hole_size_by)(shape_polygon)
            polygons.append(shape_polygon)

        return union()(*polygons)

    def _create_ledge(self, outline_shape: geometry.Shape) -> OpenSCADObject:
        """Create a polygon for the ledge around the board outline.

        Used to align the stencil with the PCB.
        """
        # Create an offset version of the outline - this is the outer edge of the ledge
        offset_outline_shape = geometry.offset_shape(list(outline_shape), 1.2)
        offset_outline_polygon = polygon([v.as_tuple() for v in offset_outline_shape])

        # A polygon of the board outline itself - cut out to leave just the ledge
        outline_polygon = polygon([v.as_tuple() for v in outline_shape])

        full_ledge_polygon = offset_outline_polygon - outline_polygon

        if self.full_ledge:
            return full_ledge_polygon

        # Cut the ledge in half by taking the bounding box of the outline, cutting it in half
        # and removing the resulting shape from the ledge shape.
        # We always leave the longer side of the ledge intact.
        cutter = geometry.bounding_box(offset_outline_shape)
        height = abs(cutter[1][1] - cutter[0][1])
        width = abs(cutter[0][0] - cutter[3][0])

        if width > height:
            cutter[1].y -= height / 2
            cutter[2].y -= height / 2
        else:
            cutter[2].x -= width / 2
            cutter[3].x -= width / 2

        return full_ledge_polygon - polygon([v.as_tuple() for v in cutter])
