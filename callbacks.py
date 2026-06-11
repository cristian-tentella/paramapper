import math

import bpy  # type: ignore

from .constants import PM
from .engine.materials import find_bsdf_and_set_color

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


def apply_fast_updates(obj):
    props = obj.paramapper
    modifier = obj.modifiers.get(PM.Objects.MODIFIER)
    if not modifier or not modifier.node_group:
        return

    nodes = modifier.node_group.nodes

    n_spread = nodes.get(PM.Nodes.SPREAD)
    if n_spread:
        n_spread.inputs["X"].default_value = props.bounds_size[0]
        n_spread.inputs["Y"].default_value = props.bounds_size[1]
        n_spread.inputs["Z"].default_value = props.bounds_size[2]

    n_gscale = nodes.get(PM.Nodes.GLOBAL_SCALE)
    if n_gscale:
        n_gscale.inputs["X"].default_value = props.global_scale
        n_gscale.inputs["Y"].default_value = props.global_scale
        n_gscale.inputs["Z"].default_value = props.global_scale

    n_tsize = nodes.get(PM.Nodes.TEXT_SIZE)
    if n_tsize:
        for axis in ["X", "Y", "Z"]:
            n_tsize.inputs[axis].default_value = props.text_size

    n_toffset = nodes.get(PM.Nodes.TEXT_OFFSET)
    if n_toffset:
        for i, axis in enumerate(["X", "Y", "Z"]):
            n_toffset.inputs[axis].default_value = props.text_offset[i]

    n_trot = nodes.get(PM.Nodes.TEXT_ROTATION)
    if n_trot:
        for i, axis in enumerate(["X", "Y", "Z"]):
            n_trot.inputs[axis].default_value = props.text_rotation[i]

    n_buildup = nodes.get(PM.Nodes.BUILD_UP)
    if n_buildup:
        n_buildup.outputs[0].default_value = props.build_up

    mat_text = bpy.data.materials.get(f"{PM.Materials.TEXT}_{obj.name}")
    if mat_text and mat_text.use_nodes:
        find_bsdf_and_set_color(mat_text, props.text_color)

    mat_bbox = bpy.data.materials.get(f"{PM.Materials.BBOX}_{obj.name}")
    if mat_bbox and mat_bbox.use_nodes:
        find_bsdf_and_set_color(mat_bbox, props.bbox_color)


def apply_filter_updates(obj):
    mod = obj.modifiers.get(PM.Objects.MODIFIER)
    if not mod or not mod.node_group:
        return
    nodes = mod.node_group.nodes
    for idx, f in enumerate(obj.paramapper.filters):
        n_val = nodes.get(f"{PM.Nodes.FILTER_PREFIX}{idx}")
        if n_val:
            n_val.outputs[0].default_value = f.value


def update_fast(self, context):
    obj = context.active_object
    if not obj or obj.type != "MESH" or not hasattr(obj, "paramapper"):
        return
    if not obj.paramapper.auto_update or not obj.paramapper.dataset_has_been_parsed:
        return
    apply_fast_updates(obj)


def update_fast_filters(self, context):
    obj = context.active_object
    if not obj or not hasattr(obj, "paramapper") or not obj.paramapper.dataset_has_been_parsed:
        return
    apply_filter_updates(obj)


@bpy.app.handlers.persistent
def paramapper_frame_handler(scene):
    for obj in scene.objects:
        if obj.type == "MESH" and hasattr(obj, "paramapper"):
            if obj.paramapper.auto_update and obj.paramapper.dataset_has_been_parsed:
                apply_fast_updates(obj)
                apply_filter_updates(obj)


def paramapper_scale_sync_timer():
    for obj in bpy.context.scene.objects:
        if obj.type == "MESH" and hasattr(obj, "paramapper"):
            props = obj.paramapper
            if not props.dataset_has_been_parsed:
                continue

            scale = obj.scale

            if (
                math.isclose(scale[0], 1.0, abs_tol=1e-4)
                and math.isclose(scale[1], 1.0, abs_tol=1e-4)
                and math.isclose(scale[2], 1.0, abs_tol=1e-4)
            ):
                obj[PM.Keys.LAST_SCALE] = [1.0, 1.0, 1.0]
                continue

            last_scale = obj.get(PM.Keys.LAST_SCALE, [0.0, 0.0, 0.0])

            if (
                math.isclose(scale[0], last_scale[0], abs_tol=1e-5)
                and math.isclose(scale[1], last_scale[1], abs_tol=1e-5)
                and math.isclose(scale[2], last_scale[2], abs_tol=1e-5)
            ):
                props.bounds_size = (
                    max(0.01, props.bounds_size[0] * scale[0]),
                    max(0.01, props.bounds_size[1] * scale[1]),
                    max(0.01, props.bounds_size[2] * scale[2]),
                )

                obj.scale = (1.0, 1.0, 1.0)
                obj[PM.Keys.LAST_SCALE] = [1.0, 1.0, 1.0]
            else:
                obj[PM.Keys.LAST_SCALE] = [scale[0], scale[1], scale[2]]

    return 0.1


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
