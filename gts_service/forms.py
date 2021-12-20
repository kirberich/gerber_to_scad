from django import forms


class UploadForm(forms.Form):
    outline_file = forms.FileField(label="Outline layer file")
    solderpaste_file = forms.FileField(label="Solder paste layer file")
    stencil_thickness = forms.FloatField(
        label="Thickness (in mm) of the stencil. Make sure this is a multiple of the layer height you use for printing.",
        initial=0.2,
    )
    include_ledge = forms.BooleanField(
        label="Include a ledge around half the outline of the board, to allow aligning the stencil easily.",
        initial=True,
        required=False,
    )
    ledge_height = forms.FloatField(
        label="Height of the stencil ledge. This should be less than the thickness of the PCB.",
        initial=1.2,
    )
    ledge_gap = forms.FloatField(
        label="Gap (in mm) between board and stencil ledge. Increase this if the fit of the stencil is too tight.",
        initial=0.0,
    )
    increase_hole_size_by = forms.FloatField(
        label="Increase the size of all holes in the stencil by this amount (in mm). Use this if you find holes get printed smaller than they should.",
        initial=0.0,
    )
    simplify_regions = forms.BooleanField(
        label="Replace regions (usually rounded rectangles) with bounding boxes. Use this if you find the processing takes extremely long, but note it might have unintended effects other than removing rounded corners.",
        initial=False,
        required=False,
    )
    flip_stencil = forms.BooleanField(
        label="Flip the stencil (use this for bottom layer stencils)",
        initial=False,
        required=False,
    )
