import math

import bpy  # type: ignore

from .constants import PM
from .engine.materials import find_bsdf_and_set_color


def _get_props(context: bpy.types.Context):
    active_object = context.active_object

    if not active_object or active_object.type != "MESH":
        return None

    return active_object.paramapper


def update_infographic(_, context: bpy.types.Context):
    if not (props := _get_props(context)):
        return

    if not props.auto_update or not props.dataset_has_been_parsed:
        return

    props.needs_rebuild = True


def apply_fast_updates(props, obj: bpy.types.Object):
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


def apply_filter_updates(obj: bpy.types.Object):
    mod = obj.modifiers.get(PM.Objects.MODIFIER)
    if not mod or not mod.node_group:
        return
    nodes = mod.node_group.nodes
    for idx, f in enumerate(obj.paramapper.filters):
        n_val = nodes.get(f"{PM.Nodes.FILTER_PREFIX}{idx}")
        if n_val:
            n_val.outputs[0].default_value = f.value


def update_fast(_, context: bpy.types.Context):
    if not (props := _get_props(context)):
        return

    if not props.auto_update or not props.dataset_has_been_parsed:
        return

    apply_fast_updates(props, context.active_object)


def update_fast_filters(_, context: bpy.types.Context):
    if not (props := _get_props(context)):
        return

    if not props.auto_update or not props.dataset_has_been_parsed:
        return

    apply_filter_updates(context.active_object)


@bpy.app.handlers.persistent
def paramapper_frame_handler(scene):
    for obj in scene.objects:
        if obj.type == "MESH":
            if obj.paramapper.auto_update and obj.paramapper.dataset_has_been_parsed:
                apply_fast_updates(obj.paramapper, obj)
                apply_filter_updates(obj)


def paramapper_rebuild_timer():
    for obj in bpy.context.scene.objects:
        if obj.type != "MESH":
            continue

        props = obj.paramapper

        if not props.needs_rebuild:
            continue

        props.needs_rebuild = False
        bpy.ops.paramapper.generate_nodes("INVOKE_DEFAULT")

    return 0.1


def _vec_isclose(a, b, abs_tol: float) -> bool:
    return (
        math.isclose(a[0], b[0], abs_tol)
        and math.isclose(a[1], b[1], abs_tol)
        and math.isclose(a[2], b[2], abs_tol)
    )


def paramapper_scale_sync_timer():
    for obj in bpy.context.scene.objects:
        if obj.type == "MESH":
            props = obj.paramapper
            if not props.dataset_has_been_parsed:
                continue

            scale = obj.scale

            if _vec_isclose(scale, (1.0, 1.0, 1.0), 1e-4):
                obj[PM.Keys.LAST_SCALE] = [1.0, 1.0, 1.0]
                continue

            last_scale = obj.get(PM.Keys.LAST_SCALE, [0.0, 0.0, 0.0])

            if _vec_isclose(scale, last_scale, 1e-5):
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


def get_numeric_columns(self, context: bpy.types.Context) -> list[tuple[str, str, str]]:
    items: list[tuple[str, str, str]] = [("NONE", "None", "Disable mapping for this axis")]

    for col in self.columns:
        if col.data_type in {"NUMERIC", "DATETIME"}:
            if col.data_type == "NUMERIC":
                tooltip = f"Map the numeric column {col.name}. Range: {col.min_val:.2f} to {col.max_val:.2f}"
                items.append((col.name, col.name, tooltip))
            else:
                tooltip = f"Map the datetime column {col.name}"
                items.append((col.name, f"{col.name} (Datetime)", tooltip))

    return items


def get_categorical_columns(self, context: bpy.types.Context) -> list[tuple[str, str, str]]:
    items: list[tuple[str, str, str]] = [("NONE", "None", "No text tag")]

    for col in self.columns:
        if col.data_type == "CATEGORICAL":
            items.append((col.name, col.name, f"Use {col.name} texts as tags"))
    return items


def get_filter_columns(self, context: bpy.types.Context):
    if not (props := _get_props(context)):
        return [("NONE", "None", "")]

    items = [("NONE", "Select column...", "")]

    for col in props.columns:
        if col.data_type == "NUMERIC":
            tooltip = f"Filter by {col.name} (Min: {col.min_val:.2f}, Max: {col.max_val:.2f})"
            items.append((col.name, col.name, tooltip))

    return items
