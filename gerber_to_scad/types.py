from pydantic import BaseModel, Field
from pygerber.gerberx3.api.v2 import ParsedFile


class Ledge(BaseModel):
    is_full_ledge: bool = Field(
        title="Full Ledge",
        description="Instead of going halfway around the board, extend the ledge to surround the entire board.",
    )
    thickness: float = Field(
        title="Ledge Thickness (mm). Should be less than the PCB thickness!",
        default=1.2,
    )


class Frame(BaseModel):
    width: float = Field(title="Frame Width (mm)")
    height: float = Field(title="Frame Height (mm)")
    thickness: float = Field(title="Frame Thickness (mm)")


class Stencil(BaseModel):
    """Converts parsed gerber outline and solderpaste files into an OpenSCAD stencil."""

    outline_file: ParsedFile = Field(
        title="Outline File", description="The outline layer"
    )
    solderpaste_file: ParsedFile = Field(
        title="Solderpaste File",
        description="The solderpaste layer - use either top or bottom. For bottom stencils, you will likely also want to enable 'Flip Stencil'",
    )
    alignment_aid: Ledge | Frame | None = Field(
        title="Alignment Aid Type",
        default_factory=lambda: Ledge(is_full_ledge=False, thickness=1.2),
    )
    thickness: float = Field(
        title="Thickness",
        description="Thickness of the stencil, in mm. Make sure this is a multiple of the layer height used when printing.",
        default=0.2,
    )
    gap: float = Field(
        title="Gap",
        default=0,
        description="Gap between the stencil and the frame/ledge. Use this if the fit is too tight or loose.",
    )
    increase_hole_size_by: float = Field(
        title="Increase hole size by",
        default=0,
        description=(
            "Increase the size of all holes in the stencil by this amount (in mm). "
            "Use this if you find holes get printed smaller than they should. "
            "Use negative values to increase the space between tightly spaced pads at the cost of making the pads smaller."
        ),
    )
    flip_stencil: bool = Field(
        title="Flip Stencil",
        default=False,
        description="Flip the stencil - use this for bottom layer stencils.",
    )
