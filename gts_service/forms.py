from django import forms

forms.Widget()


class ConvertGerberForm(forms.Form):
    solderpaste_file = forms.FileField(label="Solder paste layer file")
    outline_file = forms.FileField(label="Outline layer file")
    stencil_thickness = forms.FloatField(
        label="Thickness (in mm) of the stencil. Make sure this is a multiple of the layer height you use for printing.",
        initial=0.2,
    )
    gap = forms.FloatField(
        label="Gap (in mm) around the board outline. Increase this if the fit of the stencil in the ledge/frame is too tight.",
        initial=0.0,
    )
    include_ledge = forms.BooleanField(
        label="Include a ledge around half the outline of the board, to allow aligning the stencil more easily.",
        initial=True,
        required=False,
        widget=forms.CheckboxInput(attrs={"class": "collapse-checkbox include-ledge"}),
    )
    full_ledge = forms.BooleanField(
        label="Extend the ledge all the way around the board",
        initial=False,
        required=False,
        widget=forms.CheckboxInput(attrs={"class": "collapse-checkbox"}),
    )
    ledge_thickness = forms.FloatField(
        label="Thickness of the stencil ledge. This should be less than the thickness of the PCB.",
        initial=1.2,
    )
    increase_hole_size_by = forms.FloatField(
        label="Increase the size of all holes in the stencil by this amount (in mm). Use this if you find holes get printed smaller than they should.",
        initial=0.0,
        help_text="Use negative values to increase the space between tightly spaced pads at the cost of making the pads smaller.",
    )
    flip_stencil = forms.BooleanField(
        label="Flip the stencil (use this for bottom layer stencils)",
        initial=False,
        required=False,
    )
    include_frame = forms.BooleanField(
        label="Add a thicker frame around the stencil. Allows using the stencil in consistently-sized fixtures.",
        initial=False,
        required=False,
        widget=forms.CheckboxInput(attrs={"class": "collapse-checkbox include-frame"}),
    )
    frame_width = forms.FloatField(
        label="Width of the stencil frame (in mm).",
        initial=155,
    )
    frame_height = forms.FloatField(
        label="Height of the stencil frame (in mm).",
        initial=155,
    )
    frame_thickness = forms.FloatField(
        label="Width of the stencil frame (in mm).",
        initial=1.2,
    )
