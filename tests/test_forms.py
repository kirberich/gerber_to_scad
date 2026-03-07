from django import forms

from gts_service.forms import ConvertGerberForm


def test_form_generation():
    Form = ConvertGerberForm
    assert isinstance(Form.base_fields["outline_file"], forms.FileField)
    assert isinstance(Form.base_fields["solderpaste_file"], forms.FileField)
    assert isinstance(Form.base_fields["thickness"], forms.FloatField)
    assert isinstance(Form.base_fields["gap"], forms.FloatField)
    assert isinstance(Form.base_fields["increase_hole_size_by"], forms.FloatField)
    assert isinstance(Form.base_fields["flip_stencil"], forms.BooleanField)

    field = Form.base_fields["alignment_aid"]
    assert isinstance(field, forms.ChoiceField)
    assert isinstance(field.widget, forms.RadioSelect)
    assert field.choices == [
        ("ledge", "Ledge"),
        ("frame", "Frame"),
        ("none", "None"),
    ]

    assert isinstance(Form.base_fields["ledge__is_full_ledge"], forms.BooleanField)
    assert Form.base_fields["ledge__is_full_ledge"].initial is None
    assert isinstance(Form.base_fields["ledge__thickness"], forms.FloatField)
    assert Form.base_fields["ledge__thickness"].required is False

    assert isinstance(Form.base_fields["frame__width"], forms.FloatField)
    assert isinstance(Form.base_fields["frame__height"], forms.FloatField)
    assert isinstance(Form.base_fields["frame__thickness"], forms.FloatField)
    assert Form.base_fields["frame__width"].required is False
    assert Form.base_fields["frame__height"].required is False
    assert Form.base_fields["frame__thickness"].required is False
