import types
from collections import defaultdict
from logging import getLogger
from typing import Any, Callable, Literal, TypeVar, Union, get_args, get_origin

from django import forms
from django.core.files.uploadedfile import InMemoryUploadedFile
from django.forms.utils import ErrorList
from pydantic import BaseModel
from pydantic.fields import FieldInfo
from pydantic_core import PydanticUndefined
from pygerber.gerberx3.api.v2 import GerberFile, ParsedFile

from gerber_to_scad.types import Frame, Stencil, Ledge


logger = getLogger(__name__)


def _is_pydantic_model(t: Any) -> bool:
    try:
        return issubclass(t, BaseModel)
    except TypeError:
        return False


def _get_default(field_info: FieldInfo) -> Any:
    """Return the field's default value, or PydanticUndefined if none is set."""
    if field_info.default_factory is not None:
        return field_info.default_factory()  # type: ignore[misc]
    if field_info.default is not PydanticUndefined:
        return field_info.default
    return PydanticUndefined


def _field_from_annotation(
    field_name: str,
    field_info: FieldInfo,
    is_required_override: bool | None = None,
) -> forms.Field:
    raw_default = _get_default(field_info)
    default = None if raw_default is PydanticUndefined else raw_default

    annotation = field_info.annotation
    origin = get_origin(annotation)
    label = field_info.title or field_name
    help_text = field_info.description or ""
    is_required = (
        is_required_override
        if is_required_override is not None
        else field_info.is_required()
    )

    if origin is Literal:
        return forms.ChoiceField(
            choices=[(v, str(v)) for v in get_args(annotation)],
            initial=default,
            label=label,
            help_text=help_text,
            required=is_required,
            widget=forms.RadioSelect,
        )

    if annotation is bool:
        return forms.BooleanField(
            initial=default,
            label=label,
            help_text=help_text,
            required=False,
        )

    if annotation in (float, int):
        return forms.FloatField(
            initial=default,
            label=label,
            help_text=help_text,
            required=is_required,
        )

    if annotation is ParsedFile:
        return forms.FileField(
            initial=default,
            label=label,
            help_text=help_text,
            required=is_required,
        )
    raise ValueError(f"No Django form field mapping for type {annotation!r}")


def _flatten_nested_models(
    field_name: str, field_info: FieldInfo
) -> dict[str, forms.Field]:
    """For a union containing Pydantic models (and optionally None), generate a
    discriminator ChoiceField plus flattened sub-fields for each model type,
    named {model_name_lower}_{field_name}."""
    annotation = field_info.annotation
    args = get_args(annotation)
    model_types = [a for a in args if _is_pydantic_model(a)]
    has_none = type(None) in args

    choices = [(t.__name__.lower(), t.__name__) for t in model_types]
    if has_none:
        choices.append(("none", "None"))

    default = _get_default(field_info)
    if default is PydanticUndefined:
        initial = None
    elif model_types:
        initial = next(
            (t.__name__.lower() for t in model_types if isinstance(default, t)),
            None,
        )
    else:
        initial = default

    discriminator = forms.ChoiceField(
        choices=choices,
        label=field_info.title or field_name,
        help_text=field_info.description or "",
        required=True,
        widget=forms.RadioSelect,
        initial=initial,
    )

    result: dict[str, forms.Field] = {field_name: discriminator}
    for model_type in model_types:
        prefix = model_type.__name__.lower()
        for sub_name, sub_field_info in model_type.model_fields.items():
            flat_name = f"{prefix}__{sub_name}"
            result[flat_name] = _field_from_annotation(
                sub_name,
                sub_field_info,
                is_required_override=False,  # subfields cannot be required
            )

    return result


def form_from_schema(schema: type[BaseModel]) -> type[forms.Form]:
    """Generate a Django Form class from a Pydantic schema."""

    django_fields: dict[str, Any] = {}

    for name, field_info in schema.model_fields.items():
        annotation = field_info.annotation
        origin = get_origin(annotation)
        is_union = origin is Union or isinstance(annotation, types.UnionType)  # pyright:ignore

        if is_union and any(_is_pydantic_model(a) for a in get_args(annotation)):
            django_fields.update(_flatten_nested_models(name, field_info))
            continue

        django_fields[name] = _field_from_annotation(name, field_info)

    return type(schema.__name__ + "Form", (forms.Form,), django_fields)


ConvertGerberForm = form_from_schema(Stencil)

T = TypeVar("T")


class InvalidInput(Exception):
    errors: dict[str, ErrorList]

    def __init__(self, errors: dict[str, ErrorList]) -> None:
        self.errors = errors
        super().__init__()


def _required(
    field_name: str,
    cleaned_data: dict[str, Any],
    errors: dict[str, ErrorList],
) -> T | None:
    value = cleaned_data.get(field_name)
    if value is None:
        errors[field_name].append(f"{field_name} is required.")
        return

    return value


def stencil_from_form(form: forms.Form):
    if form.is_valid():
        errors: dict[str, ErrorList] = defaultdict(ErrorList)
    else:
        errors = form.errors

    cleaned_data = form.cleaned_data

    outline_file = cleaned_data["outline_file"]
    assert isinstance(outline_file, InMemoryUploadedFile)
    solder_paste = cleaned_data["solderpaste_file"]
    assert isinstance(solder_paste, InMemoryUploadedFile)

    try:
        outline = GerberFile.from_str(outline_file.read().decode("utf-8")).parse()
    except Exception as e:
        errors["outline_file"].append(f"Outline file is not a valid gerber file. {e}")
        outline = None

    try:
        solder_paste = GerberFile.from_str(solder_paste.read().decode("utf-8")).parse()
    except Exception as e:
        errors["solderpaste_file"].append(
            f"Solder paste file is not a valid gerber file. {e}"
        )
        solder_paste = None

    alignment_type = cleaned_data["alignment_aid"]
    assert alignment_type in ("ledge", "frame", "none"), (
        f"Invalid alignment type {alignment_type}"
    )

    alignment_aid = None
    match alignment_type:
        case "ledge":
            alignment_aid = Ledge(
                is_full_ledge=bool(cleaned_data.get("ledge__is_full_ledge")),
                thickness=_required("ledge__thickness", cleaned_data, errors) or 0,
            )
        case "frame":
            alignment_aid = Frame(
                width=_required("frame__width", cleaned_data, errors) or 0,
                height=_required("frame__height", cleaned_data, errors) or 0,
                thickness=_required("frame__thickness", cleaned_data, errors) or 0,
            )
        case "none":
            pass

    if errors:
        raise InvalidInput(errors)

    assert outline is not None
    assert solder_paste is not None

    return Stencil(
        outline_file=outline,
        solderpaste_file=solder_paste,
        alignment_aid=alignment_aid,
        thickness=cleaned_data["thickness"],
        gap=cleaned_data["gap"],
        increase_hole_size_by=cleaned_data["increase_hole_size_by"],
        flip_stencil=cleaned_data["flip_stencil"],
    )
