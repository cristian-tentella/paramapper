import bpy  # type: ignore

from .constants import ParamapperNames

_numeric_cache = []
_filter_cache = []

def update_infographic(self, context):
    obj = context.active_object
    if not obj or not hasattr(obj, "paramapper"):
        return

    props = obj.paramapper

    if not props.auto_update or not props.dataset_has_been_parsed:
        return

    try:
        bpy.ops.paramapper.generate_nodes("INVOKE_DEFAULT")
    except RuntimeError:
        pass


def update_fast(self, context):
    obj = context.active_object
    if not obj or obj.type != "MESH" or not hasattr(obj, "paramapper"):
        return

    props = obj.paramapper

    if not props.auto_update or not props.dataset_has_been_parsed:
        return

    modifier = obj.modifiers.get(ParamapperNames.MODIFIER)
    if not modifier or not modifier.node_group:
        return

    nodes = modifier.node_group.nodes

    n_spread = nodes.get(ParamapperNames.NODE_SPREAD)
    if n_spread:
        n_spread.inputs["X"].default_value = props.bounds_size[0]
        n_spread.inputs["Y"].default_value = props.bounds_size[1]
        n_spread.inputs["Z"].default_value = props.bounds_size[2]

    n_gscale = nodes.get(ParamapperNames.NODE_GLOBAL_SCALE)
    if n_gscale:
        n_gscale.inputs["X"].default_value = props.global_scale
        n_gscale.inputs["Y"].default_value = props.global_scale
        n_gscale.inputs["Z"].default_value = props.global_scale

    n_tsize = nodes.get(ParamapperNames.NODE_TEXT_SIZE)
    if n_tsize:
        for axis in ["X", "Y", "Z"]:
            n_tsize.inputs[axis].default_value = props.text_size

    n_toffset = nodes.get(ParamapperNames.NODE_TEXT_OFFSET)
    if n_toffset:
        for i, axis in enumerate(["X", "Y", "Z"]):
            n_toffset.inputs[axis].default_value = props.text_offset[i]

    n_trot = nodes.get(ParamapperNames.NODE_TEXT_ROTATION)
    if n_trot:
        for i, axis in enumerate(["X", "Y", "Z"]):
            n_trot.inputs[axis].default_value = props.text_rotation[i]

    mat_text = bpy.data.materials.get(f"{ParamapperNames.TEXT_MATERIAL}_{obj.name}")
    if mat_text and mat_text.use_nodes:
        node_principled = next(
            (n for n in mat_text.node_tree.nodes if n.type == "BSDF_PRINCIPLED"), None
        )
        if node_principled:
            node_principled.inputs["Base Color"].default_value = props.text_color

    mat_bbox = bpy.data.materials.get(f"{ParamapperNames.BBOX_MATERIAL}_{obj.name}")
    if mat_bbox and mat_bbox.use_nodes:
        node_principled = next(
            (n for n in mat_bbox.node_tree.nodes if n.type == "BSDF_PRINCIPLED"), None
        )
        if node_principled:
            node_principled.inputs["Base Color"].default_value = props.bbox_color


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


def get_numeric_columns(self, context) -> list[tuple[str, str, str]]:
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


def get_categorical_columns(self, context) -> list[tuple[str, str, str]]:
    items: list[tuple[str, str, str]] = [("NONE", "None", "No text tag")]

    for col in self.columns:
        if col.data_type == "CATEGORICAL":
            items.append((col.name, col.name, f"Use {col.name} texts as tags"))
    return items


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
