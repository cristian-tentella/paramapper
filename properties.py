from typing import Any

import bpy  # type: ignore

from .constants import ParamapperNames  # type: ignore

_numeric_cache = []
_filter_cache = []


class PARAMAPPER_PG_ColumnMeta(bpy.types.PropertyGroup):
    name: bpy.props.StringProperty(name="Column Name")  # type: ignore

    data_type: bpy.props.EnumProperty(  # type: ignore
        name="Data Type",
        items=[
            ("NUMERIC", "Numeric", ""),
            ("CATEGORICAL", "Categorical", ""),
            ("DATETIME", "Datetime", ""),
        ],
        default="NUMERIC",
    )

    min_val: bpy.props.FloatProperty(name="Min Value", default=0.0)  # type: ignore
    max_val: bpy.props.FloatProperty(name="Max Value", default=0.0)  # type: ignore

    unique_tokens: bpy.props.StringProperty(name="Unique Tokens", default="")  # type: ignore


def get_filter_columns(self, context):
    global _filter_cache

    obj = context.active_object
    if not obj or not hasattr(obj, "paramapper"):
        return [("NONE", "None", "")]

    items = [("NONE", "Select column...", "")]
    for col in obj.paramapper.columns:
        if col.data_type == "NUMERIC":
            tooltip = f"Filter by {col.name} (Min: {col.min_val:.2f}, Max: {col.max_val:.2f})"
            items.append((col.name, col.name, tooltip))

    _filter_cache = items
    return items


class PARAMAPPER_PG_FilterItem(bpy.types.PropertyGroup):
    column: bpy.props.EnumProperty(
        name="Column",
        items=get_filter_columns,
        update=lambda self, context: bpy.ops.paramapper.generate_nodes("INVOKE_DEFAULT"),
    )  # type: ignore

    operation: bpy.props.EnumProperty(
        name="Operation",
        items=[
            ("GREATER_THAN", ">", "Greater Than"),
            ("LESS_THAN", "<", "Less Than"),
            ("EQUAL", "==", "Equal To"),
            ("NOT_EQUAL", "!=", "Not Equal"),
        ],
        default="GREATER_THAN",
        update=lambda self, context: bpy.ops.paramapper.generate_nodes("INVOKE_DEFAULT"),
    )  # type: ignore

    value: bpy.props.FloatProperty(
        name="Value", default=0.0, update=lambda self, context: update_fast_filters(self, context)
    )  # type: ignore


def update_infographic(self, context):
    if getattr(self, "auto_update", False) and getattr(self, "dataset_has_been_parsed", False):
        try:
            bpy.ops.paramapper.generate_nodes("INVOKE_DEFAULT")
        except RuntimeError:
            pass


def update_fast(self, context):
    if not getattr(self, "auto_update", False) or not getattr(
        self, "dataset_has_been_parsed", False
    ):
        return

    obj = context.active_object
    if not obj or obj.type != "MESH":
        return

    from .constants import ParamapperNames

    modifier = obj.modifiers.get(ParamapperNames.MODIFIER)
    if not modifier or not modifier.node_group:
        return

    nodes = modifier.node_group.nodes

    n_spread = nodes.get(ParamapperNames.NODE_SPREAD)
    if n_spread:
        n_spread.inputs["X"].default_value = self.spread_vector[0]
        n_spread.inputs["Y"].default_value = self.spread_vector[1]
        n_spread.inputs["Z"].default_value = self.spread_vector[2]

    n_gscale = nodes.get(ParamapperNames.NODE_GLOBAL_SCALE)
    if n_gscale:
        n_gscale.inputs["X"].default_value = self.global_scale
        n_gscale.inputs["Y"].default_value = self.global_scale
        n_gscale.inputs["Z"].default_value = self.global_scale

    n_tsize = nodes.get(ParamapperNames.NODE_TEXT_SIZE)
    if n_tsize:
        for _, axis in enumerate(["X", "Y", "Z"]):
            n_tsize.inputs[axis].default_value = self.text_size

    n_toffset = nodes.get(ParamapperNames.NODE_TEXT_OFFSET)
    if n_toffset:
        for i, axis in enumerate(["X", "Y", "Z"]):
            n_toffset.inputs[axis].default_value = self.text_offset[i]

    n_trot = nodes.get(ParamapperNames.NODE_TEXT_ROTATION)
    if n_trot:
        for i, axis in enumerate(["X", "Y", "Z"]):
            n_trot.inputs[axis].default_value = self.text_rotation[i]

    mat_text = bpy.data.materials.get(f"{ParamapperNames.TEXT_MATERIAL}_{obj.name}")
    if mat_text and mat_text.use_nodes:
        node_principled = next(
            (n for n in mat_text.node_tree.nodes if n.type == "BSDF_PRINCIPLED"), None
        )
        if node_principled:
            node_principled.inputs["Base Color"].default_value = self.text_color

    mat_bbox = bpy.data.materials.get(f"{ParamapperNames.BBOX_MATERIAL}_{obj.name}")
    if mat_bbox and mat_bbox.use_nodes:
        node_principled = next(
            (n for n in mat_bbox.node_tree.nodes if n.type == "BSDF_PRINCIPLED"), None
        )
        if node_principled:
            node_principled.inputs["Base Color"].default_value = self.bbox_color


def update_fast_filters(self, context):
    obj = context.active_object
    if not obj or not obj.paramapper.dataset_has_been_parsed:
        return

    mod = obj.modifiers.get(ParamapperNames.MODIFIER)
    if not mod or not mod.node_group:
        return

    nodes = mod.node_group.nodes
    for idx, f in enumerate(obj.paramapper.filters):
        n_val = nodes.get(f"ParamapperFilter_{idx}")
        if n_val:
            n_val.outputs[0].default_value = f.value


class PARAMAPPER_PG_Settings(bpy.types.PropertyGroup):
    def reset_to_defaults(self):
        self.filters.clear()
        self.active_filter_index = 0

        self.map_x = "NONE"
        self.map_y = "NONE"
        self.map_z = "NONE"
        self.map_scale = "NONE"
        self.map_color = "NONE"
        self.map_text = "NONE"

        self.show_bounding_box = True


    dataset_path: bpy.props.StringProperty(  # type: ignore
        name="Dataset path",
        description="",
        default="",
    )

    last_parsed_path: bpy.props.StringProperty(default="")  # type: ignore

    dataset_has_been_parsed: bpy.props.BoolProperty(  # type: ignore
        name="Dataset has been parsed", default=False
    )

    auto_update: bpy.props.BoolProperty(  # type: ignore
        name="Live Update",
        description="Automatically regenerate the infographic when a property changes",
        default=True,
    )

    filters: bpy.props.CollectionProperty(type=PARAMAPPER_PG_FilterItem)  # type: ignore
    active_filter_index: bpy.props.IntProperty(name="Active Filter Index", default=0)  # type: ignore

    show_bounding_box: bpy.props.BoolProperty(  # type: ignore
        name="Show Bounding Box",
        description="Display a wireframe bounding box around the dataset",
        default=True,
        update=update_infographic,
    )

    bbox_color: bpy.props.FloatVectorProperty(  # type: ignore
        name="Bounding Box Color",
        subtype="COLOR",
        default=(1.0, 1.0, 1.0, 1.0),
        size=4,
        min=0.0,
        max=1.0,
        update=update_fast,
    )

    parsed_row_count: bpy.props.IntProperty(  # type: ignore
        name="Row Count", default=0
    )

    columns: bpy.props.CollectionProperty(type=PARAMAPPER_PG_ColumnMeta)  # type: ignore

    # Callbacks

    def _get_numeric_columns(self, context: Any) -> list[tuple[str, str, str]]:
        global _numeric_cache

        items: list[tuple[str, str, str]] = [("NONE", "None", "Disable mapping for this axis")]

        for col in self.columns:
            if col.data_type in {"NUMERIC", "DATETIME"}:
                if col.data_type == "NUMERIC":
                    tooltip = f"Map the numeric column {col.name}. Range: {col.min_val:.2f} to {col.max_val:.2f}"
                    items.append((col.name, col.name, tooltip))
                else:
                    tooltip = f"Map the datetime column {col.name}"
                    items.append((col.name, f"{col.name} (Datetime)", tooltip))

        _numeric_cache = items
        return items

    def _get_categorical_columns(self, context: Any) -> list[tuple[str, str, str]]:
        items: list[tuple[str, str, str]] = [("NONE", "None", "No text tag")]

        for col in self.columns:
            if col.data_type == "CATEGORICAL":
                items.append((col.name, col.name, f"Use {col.name} texts as tags"))
        return items

    # Mapping properties

    map_x: bpy.props.EnumProperty(
        name="X Axis", items=_get_numeric_columns, update=update_infographic
    )  # type: ignore
    map_y: bpy.props.EnumProperty(
        name="Y Axis", items=_get_numeric_columns, update=update_infographic
    )  # type: ignore
    map_z: bpy.props.EnumProperty(
        name="Z Axis", items=_get_numeric_columns, update=update_infographic
    )  # type: ignore

    spread_vector: bpy.props.FloatVectorProperty(  # type: ignore
        name="Spread (X,Y,Z)",
        subtype="XYZ",
        default=(1.0, 1.0, 1.0),
        size=3,
        min=0.01,
        update=update_fast,
    )

    map_scale: bpy.props.EnumProperty(
        name="Scale", items=_get_numeric_columns, update=update_infographic
    )  # type: ignore

    global_scale: bpy.props.FloatProperty(  # type: ignore
        name="Global Scale", default=1.0, min=0.01, update=update_fast
    )

    map_color: bpy.props.EnumProperty(  # type: ignore
        name="Color", items=_get_numeric_columns, update=update_infographic
    )

    instance_object: bpy.props.PointerProperty(  # type: ignore
        name="Instance Model", type=bpy.types.Object, update=update_infographic
    )

    override_material: bpy.props.BoolProperty(  # type: ignore
        name="Override Custom Material",
        description="Apply Paramapper's data colors instead of the model's original material",
        default=False,
        update=update_infographic,
    )

    map_text: bpy.props.EnumProperty(
        name="Text Label", items=_get_categorical_columns, update=update_infographic
    )  # type: ignore

    text_size: bpy.props.FloatProperty(  # type: ignore
        name="Text Size", default=1.0, min=0.01, update=update_fast
    )

    text_thickness: bpy.props.FloatProperty(  # type: ignore
        name="Text Thickness", default=0.0, min=0.0, update=update_infographic
    )

    text_offset: bpy.props.FloatVectorProperty(  # type: ignore
        name="Text Offset", subtype="XYZ", default=(0.0, 0.0, 1.5), size=3, update=update_fast
    )

    text_rotation: bpy.props.FloatVectorProperty(  # type: ignore
        name="Text Rotation", subtype="EULER", default=(0.0, 0.0, 0.0), size=3, update=update_fast
    )

    text_color: bpy.props.FloatVectorProperty(  # type: ignore
        name="Text Color",
        subtype="COLOR",
        default=(1.0, 1.0, 1.0, 1.0),
        size=4,
        min=0.0,
        max=1.0,
        update=update_fast,
    )
