import bpy  # type: ignore

from .constants import ParamapperNames


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
