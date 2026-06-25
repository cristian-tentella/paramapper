import bpy  # type: ignore

from ..constants import PM
from .ticks import generate_ticks
from .utils import GNTreeBuilder


class SpatialBuilder:
    _SCALE_MIN = 0.1
    _SCALE_MAX = 1.0

    @staticmethod
    def map_axes(props, builder: GNTreeBuilder, node_combine_xyz) -> int:
        axis_mappings = {"X": props.map_x, "Y": props.map_y, "Z": props.map_z}
        current_y = 0

        for axis, col_name in axis_mappings.items():
            if col_name == "NONE":
                continue

            col_meta = props.columns.get(col_name)
            if not col_meta:
                continue

            mapped_socket = builder.create_mapped_attribute(
                col_name,
                from_min=col_meta.min_val,
                from_max=col_meta.max_val,
                to_min=0.0,
                to_max=1.0,
                location=(-400, current_y),
            )
            builder.link(mapped_socket, node_combine_xyz.inputs[axis])
            current_y -= 250

        return current_y

    @staticmethod
    def map_scale(props, builder: GNTreeBuilder, current_geo, current_y: int):
        scale_socket = None

        if props.map_scale != "NONE":
            col_meta = props.columns.get(props.map_scale)
            if col_meta:
                scale_socket = builder.create_mapped_attribute(
                    col_name=props.map_scale,
                    from_min=col_meta.min_val,
                    from_max=col_meta.max_val,
                    to_min=SpatialBuilder._SCALE_MIN,
                    to_max=SpatialBuilder._SCALE_MAX,
                    location=(-400, current_y),
                )

                current_y -= 250

        return current_geo, scale_socket, current_y


class FilterBuilder:
    @staticmethod
    def apply_culling(props, builder, current_geo, current_y: int):
        valid_filters = [f for f in props.filters if f.column != "NONE"]

        if not valid_filters:
            return current_geo, current_y

        conditions = []

        for idx, f in enumerate(valid_filters):
            node_attr = builder.create_node("GeometryNodeInputNamedAttribute", (-800, current_y))
            node_attr.inputs["Name"].default_value = f.column
            node_attr.data_type = "FLOAT"

            node_val = builder.create_node("ShaderNodeValue", (-800, current_y - 120))
            node_val.name = f"{PM.Nodes.FILTER_PREFIX}{idx}"
            node_val.outputs[0].default_value = f.value

            node_comp = builder.create_node("FunctionNodeCompare", (-600, current_y))
            node_comp.data_type = "FLOAT"
            node_comp.operation = f.operation
            builder.link(node_attr.outputs[0], node_comp.inputs[0])
            builder.link(node_val.outputs[0], node_comp.inputs[1])

            conditions.append(node_comp.outputs[0])
            current_y -= 250

        if len(conditions) == 1:
            final_keep_socket = conditions[0]
        else:
            current_link = conditions[0]
            for i in range(1, len(conditions)):
                node_and = builder.create_node("FunctionNodeBooleanMath", (-400, current_y))
                node_and.operation = "AND"
                builder.link(current_link, node_and.inputs[0])
                builder.link(conditions[i], node_and.inputs[1])
                current_link = node_and.outputs[0]
                current_y -= 150
            final_keep_socket = current_link

        node_not = builder.create_node("FunctionNodeBooleanMath", (-200, current_y))
        node_not.operation = "NOT"
        builder.link(final_keep_socket, node_not.inputs[0])

        node_del = builder.create_node("GeometryNodeDeleteGeometry", (0, current_y))
        node_del.domain = "POINT"
        builder.link(current_geo, node_del.inputs["Geometry"])
        builder.link(node_not.outputs[0], node_del.inputs["Selection"])

        return node_del.outputs[0], current_y - 200

    @staticmethod
    def apply_auto_fit(props, builder: GNTreeBuilder, current_geo, current_y: int):
        if not props.auto_fit_bounds:
            return current_geo, current_y

        node_stat = builder.create_node("GeometryNodeAttributeStatistic", (-400, current_y))
        node_stat.data_type = "FLOAT_VECTOR"
        node_stat.domain = "POINT"

        node_pos = builder.create_node("GeometryNodeInputPosition", (-600, current_y - 100))

        builder.link(current_geo, node_stat.inputs["Geometry"])
        builder.link(node_pos.outputs[0], node_stat.inputs["Attribute"])

        node_map = builder.create_node("ShaderNodeMapRange", (-200, current_y))
        node_map.data_type = "FLOAT_VECTOR"

        builder.link(node_pos.outputs[0], node_map.inputs["Vector"])
        builder.link(node_stat.outputs["Min"], node_map.inputs["From Min"])
        builder.link(node_stat.outputs["Max"], node_map.inputs["From Max"])

        node_spread = builder.nodes.get(PM.Nodes.SPREAD)
        if node_spread:
            builder.link(node_spread.outputs[0], node_map.inputs["To Max"])

        node_set_pos = builder.create_node("GeometryNodeSetPosition", (0, current_y))
        builder.link(current_geo, node_set_pos.inputs["Geometry"])
        builder.link(node_map.outputs["Vector"], node_set_pos.inputs["Position"])

        return node_set_pos.outputs[0], current_y - 250


class VisualBuilder:
    _BASE_REDUCTION = 0.2
    _BBOX_RADIUS = 0.02
    _BBOX_RESOLUTION = 4

    @staticmethod
    def _build_text_geometry(
        props, builder: GNTreeBuilder, tokens: list[str]
    ) -> bpy.types.NodeSocket:
        node_geo_to_inst = builder.create_node("GeometryNodeGeometryToInstance", (800, -400))

        for i, token in enumerate(tokens):
            node_str = builder.create_node("GeometryNodeStringToCurves", (0, -400 - (i * 250)))
            node_str.inputs["String"].default_value = token

            node_fill = builder.create_node("GeometryNodeFillCurve", (200, -400 - (i * 250)))
            builder.link(node_str.outputs[0], node_fill.inputs[0])

            if props.text_thickness > 0.0:
                node_extrude = builder.create_node(
                    "GeometryNodeExtrudeMesh", (400, -400 - (i * 250))
                )
                node_extrude.inputs["Offset Scale"].default_value = props.text_thickness

                node_flip = builder.create_node("GeometryNodeFlipFaces", (400, -550 - (i * 250)))
                node_join_cap = builder.create_node(
                    "GeometryNodeJoinGeometry", (600, -400 - (i * 250))
                )

                builder.link(node_fill.outputs[0], node_flip.inputs[0])
                builder.link(node_flip.outputs[0], node_join_cap.inputs[0])
                builder.link(node_fill.outputs[0], node_extrude.inputs["Mesh"])
                builder.link(node_extrude.outputs["Mesh"], node_join_cap.inputs[0])

                builder.link(node_join_cap.outputs[0], node_geo_to_inst.inputs[0])
            else:
                builder.link(node_fill.outputs[0], node_geo_to_inst.inputs[0])

        return node_geo_to_inst.outputs[0]

    @staticmethod
    def instantiate_labels(props, builder: GNTreeBuilder, base_points, mat_text):
        if props.map_text == "NONE":
            return None

        col_meta = props.columns.get(props.map_text)
        if not col_meta or not col_meta.unique_tokens:
            return None

        tokens = col_meta.unique_tokens.split("\n")

        instances_socket = VisualBuilder._build_text_geometry(props, builder, tokens)

        node_text_attr = builder.create_node(
            "GeometryNodeInputNamedAttribute", (800, -600), data_type="FLOAT"
        )
        node_text_attr.inputs["Name"].default_value = props.map_text

        node_inst = builder.create_node("GeometryNodeInstanceOnPoints", (1000, -300))
        node_inst.inputs["Pick Instance"].default_value = True

        node_text_scale = builder.create_node("ShaderNodeCombineXYZ", (800, -750))
        node_text_scale.name = PM.Nodes.TEXT_SIZE
        node_text_scale.inputs["X"].default_value = props.text_size
        node_text_scale.inputs["Y"].default_value = props.text_size
        node_text_scale.inputs["Z"].default_value = props.text_size

        builder.link(node_text_scale.outputs[0], node_inst.inputs["Scale"])
        builder.link(base_points, node_inst.inputs["Points"])
        builder.link(instances_socket, node_inst.inputs["Instance"])
        builder.link(node_text_attr.outputs[0], node_inst.inputs["Instance Index"])

        node_translate = builder.create_node("GeometryNodeTranslateInstances", (1200, -300))
        node_trans_vec = builder.create_node("ShaderNodeCombineXYZ", (1000, -500))
        node_trans_vec.name = PM.Nodes.TEXT_OFFSET
        node_trans_vec.inputs["X"].default_value = props.text_offset[0]
        node_trans_vec.inputs["Y"].default_value = props.text_offset[1]
        node_trans_vec.inputs["Z"].default_value = props.text_offset[2]

        builder.link(node_inst.outputs[0], node_translate.inputs["Instances"])
        builder.link(node_trans_vec.outputs[0], node_translate.inputs["Translation"])

        node_rotate = builder.create_node("GeometryNodeRotateInstances", (1400, -300))
        node_rot_vec = builder.create_node("ShaderNodeCombineXYZ", (1200, -500))
        node_rot_vec.name = PM.Nodes.TEXT_ROTATION
        node_rot_vec.inputs["X"].default_value = props.text_rotation[0]
        node_rot_vec.inputs["Y"].default_value = props.text_rotation[1]
        node_rot_vec.inputs["Z"].default_value = props.text_rotation[2]

        builder.link(node_translate.outputs[0], node_rotate.inputs["Instances"])
        builder.link(node_rot_vec.outputs[0], node_rotate.inputs["Rotation"])

        node_set_mat = builder.create_node("GeometryNodeSetMaterial", (1600, -300))
        if mat_text:
            node_set_mat.inputs["Material"].default_value = mat_text

        builder.link(node_rotate.outputs[0], node_set_mat.inputs["Geometry"])

        return node_set_mat.outputs[0]

    @staticmethod
    def _build_global_scale_node(props, builder: GNTreeBuilder):
        node_global_vec = builder.create_node("ShaderNodeCombineXYZ", (200, -100))
        # Unique per build: generator.py if/else guarantees only one instantiate path runs.
        node_global_vec.name = PM.Nodes.GLOBAL_SCALE
        node_global_vec.inputs["X"].default_value = props.global_scale
        node_global_vec.inputs["Y"].default_value = props.global_scale
        node_global_vec.inputs["Z"].default_value = props.global_scale

        node_base_reduction = builder.create_node("ShaderNodeVectorMath", (400, -100))
        node_base_reduction.operation = "MULTIPLY"
        node_base_reduction.inputs[1].default_value = (VisualBuilder._BASE_REDUCTION,) * 3

        builder.link(node_global_vec.outputs[0], node_base_reduction.inputs[0])

        return node_base_reduction.outputs[0]

    @staticmethod
    def instantiate_object_models(props, builder: GNTreeBuilder, base_points, scale_socket, mat):
        reduction_node_output = VisualBuilder._build_global_scale_node(props, builder)

        node_src = builder.create_node("GeometryNodeObjectInfo", (400, 200))
        node_src.inputs["Object"].default_value = props.instance_object
        node_src.transform_space = "ORIGINAL"
        instance_socket = node_src.outputs["Geometry"]

        node_inst = builder.create_node("GeometryNodeInstanceOnPoints", (800, 100))
        builder.link(base_points, node_inst.inputs["Points"])
        builder.link(instance_socket, node_inst.inputs["Instance"])

        if scale_socket:
            node_math_scale = builder.create_node("ShaderNodeVectorMath", (600, -100))
            node_math_scale.operation = "MULTIPLY"
            builder.link(scale_socket, node_math_scale.inputs[0])
            builder.link(reduction_node_output, node_math_scale.inputs[1])
            builder.link(node_math_scale.outputs["Vector"], node_inst.inputs["Scale"])
        else:
            builder.link(reduction_node_output, node_inst.inputs["Scale"])

        current_geo = node_inst.outputs[0]

        if props.override_material:
            node_mat = builder.create_node("GeometryNodeSetMaterial", (1200, 100))
            if mat:
                node_mat.inputs["Material"].default_value = mat
            builder.link(current_geo, node_mat.inputs["Geometry"])
            return node_mat.outputs[0]
        else:
            return current_geo

    @staticmethod
    def instantiate_point_models(props, builder: GNTreeBuilder, base_points, scale_socket, mat):
        reduction_node_output = VisualBuilder._build_global_scale_node(props, builder)

        node_sep_xyz = builder.create_node("ShaderNodeSeparateXYZ", (600, -200))
        builder.link(reduction_node_output, node_sep_xyz.inputs[0])

        node_radius_math = builder.create_node("ShaderNodeMath", (800, -100))
        node_radius_math.operation = "MULTIPLY"

        if scale_socket:
            builder.link(scale_socket, node_radius_math.inputs[0])
            builder.link(node_sep_xyz.outputs["X"], node_radius_math.inputs[1])
        else:
            node_radius_math.inputs[0].default_value = 1.0
            builder.link(node_sep_xyz.outputs["X"], node_radius_math.inputs[1])

        node_set_radius = builder.create_node("GeometryNodeSetPointRadius", (1000, 100))
        builder.link(base_points, node_set_radius.inputs["Points"])
        builder.link(node_radius_math.outputs["Value"], node_set_radius.inputs["Radius"])

        current_geo = node_set_radius.outputs[0]

        node_mat = builder.create_node("GeometryNodeSetMaterial", (1200, 100))
        if mat:
            node_mat.inputs["Material"].default_value = mat
        builder.link(current_geo, node_mat.inputs["Geometry"])
        return node_mat.outputs[0]

    @staticmethod
    def map_color(props, builder: GNTreeBuilder, current_geo, current_y: int):
        if props.map_color != "NONE":
            col_meta = props.columns.get(props.map_color)
            if col_meta:
                color_socket = builder.create_mapped_attribute(
                    col_name=props.map_color,
                    from_min=col_meta.min_val,
                    from_max=col_meta.max_val,
                    to_min=0.0,
                    to_max=1.0,
                    location=(-400, current_y),
                )

                node_store = builder.create_node(
                    "GeometryNodeStoreNamedAttribute", (400, current_y)
                )
                node_store.data_type = "FLOAT"
                node_store.domain = "POINT"
                node_store.inputs["Name"].default_value = PM.Attributes.COLOR_MAP

                builder.link(current_geo, node_store.inputs["Geometry"])
                builder.link(color_socket, node_store.inputs["Value"])

                return node_store.outputs[0], current_y - 250

        return current_geo, current_y

    @staticmethod
    def add_bounding_box(props, builder: GNTreeBuilder, limits_geo, mat_bbox):
        if not props.show_bounding_box:
            return None

        node_m2c = builder.create_node("GeometryNodeMeshToCurve", (1200, 200))
        builder.link(limits_geo, node_m2c.inputs[0])

        node_c2m = builder.create_node("GeometryNodeCurveToMesh", (1400, 200))
        node_circle = builder.create_node("GeometryNodeCurvePrimitiveCircle", (1200, 50))
        node_circle.inputs["Radius"].default_value = VisualBuilder._BBOX_RADIUS
        node_circle.inputs["Resolution"].default_value = VisualBuilder._BBOX_RESOLUTION

        builder.link(node_m2c.outputs[0], node_c2m.inputs["Curve"])
        builder.link(node_circle.outputs[0], node_c2m.inputs["Profile Curve"])

        node_mat = builder.create_node("GeometryNodeSetMaterial", (1600, 200))
        if mat_bbox:
            node_mat.inputs["Material"].default_value = mat_bbox

        builder.link(node_c2m.outputs[0], node_mat.inputs["Geometry"])
        return node_mat.outputs[0]


class AnimationBuilder:
    # Controls how much stagger exists between the first and last point appearing.
    # At 0.95 the last point starts fading in when build_up reaches 0.95, not 1.0.
    _STAGGER = 0.95
    # Controls the sharpness of each point's fade-in transition.
    _SHARPNESS = 20.0

    @staticmethod
    def apply_build_up(props, builder: GNTreeBuilder, main_geo, text_geo):
        node_buildup = builder.create_node("ShaderNodeValue", (1200, 200))
        node_buildup.name = PM.Nodes.BUILD_UP
        node_buildup.outputs[0].default_value = props.build_up

        node_count = builder.create_node("ShaderNodeValue", (1200, 0))
        node_count.outputs[0].default_value = float(props.parsed_row_count)

        node_index = builder.create_node("GeometryNodeInputIndex", (1200, -200))

        node_div = builder.create_node("ShaderNodeMath", (1400, -100))
        node_div.operation = "DIVIDE"
        builder.link(node_index.outputs[0], node_div.inputs[0])
        builder.link(node_count.outputs[0], node_div.inputs[1])

        node_stagger = builder.create_node("ShaderNodeMath", (1400, -250))
        node_stagger.operation = "MULTIPLY"
        node_stagger.inputs[1].default_value = AnimationBuilder._STAGGER
        builder.link(node_div.outputs[0], node_stagger.inputs[0])

        node_sub = builder.create_node("ShaderNodeMath", (1600, 0))
        node_sub.operation = "SUBTRACT"
        builder.link(node_buildup.outputs[0], node_sub.inputs[0])
        builder.link(node_stagger.outputs[0], node_sub.inputs[1])

        node_sharpen = builder.create_node("ShaderNodeMath", (1600, -150))
        node_sharpen.operation = "MULTIPLY"
        node_sharpen.use_clamp = True
        node_sharpen.inputs[1].default_value = AnimationBuilder._SHARPNESS
        builder.link(node_sub.outputs[0], node_sharpen.inputs[0])

        node_combine = builder.create_node("ShaderNodeCombineXYZ", (1700, -100))
        builder.link(node_sharpen.outputs[0], node_combine.inputs[0])
        builder.link(node_sharpen.outputs[0], node_combine.inputs[1])
        builder.link(node_sharpen.outputs[0], node_combine.inputs[2])

        node_scale_main = builder.create_node("GeometryNodeScaleInstances", (1800, 0))
        builder.link(main_geo, node_scale_main.inputs[0])
        builder.link(node_combine.outputs[0], node_scale_main.inputs["Scale"])
        main_geo = node_scale_main.outputs[0]

        node_radius_in = builder.create_node("GeometryNodeInputRadius", (1800, -150))
        node_radius_mul = builder.create_node("ShaderNodeMath", (1800, -250))
        node_radius_mul.operation = "MULTIPLY"
        builder.link(node_radius_in.outputs[0], node_radius_mul.inputs[0])
        builder.link(node_sharpen.outputs[0], node_radius_mul.inputs[1])

        node_set_radius = builder.create_node("GeometryNodeSetPointRadius", (2000, 0))
        builder.link(main_geo, node_set_radius.inputs[0])
        builder.link(node_radius_mul.outputs[0], node_set_radius.inputs["Radius"])
        main_geo = node_set_radius.outputs[0]

        if text_geo:
            node_scale_text = builder.create_node("GeometryNodeScaleInstances", (1800, -400))
            builder.link(text_geo, node_scale_text.inputs[0])
            builder.link(node_combine.outputs[0], node_scale_text.inputs["Scale"])
            text_geo = node_scale_text.outputs[0]

        return main_geo, text_geo


class AxisBuilder:
    _OFFSET = 0.5

    @staticmethod
    def build_axis_labels(props, builder: GNTreeBuilder, mat, axis_ranges, current_y: int):
        if not props.show_axis_labels or not axis_ranges:
            return None, current_y

        node_spread = builder.nodes.get(PM.Nodes.SPREAD)
        if not node_spread:
            return None, current_y

        node_sep = builder.create_node("ShaderNodeSeparateXYZ", (-2200, current_y))
        builder.link(node_spread.outputs[0], node_sep.inputs[0])
        sep_outputs = [node_sep.outputs["X"], node_sep.outputs["Y"], node_sep.outputs["Z"]]

        axis_geos = []

        for axis_idx, min_val, max_val, data_type in axis_ranges:
            ticks = generate_ticks(
                min_val,
                max_val,
                props.axis_label_count,
                data_type,
            )

            tick_geos = []

            for tick in ticks:
                node_str = builder.create_node("GeometryNodeStringToCurves", (-2200, current_y))
                node_str.inputs["String"].default_value = tick.label

                node_fill = builder.create_node("GeometryNodeFillCurve", (-2000, current_y))
                builder.link(node_str.outputs[0], node_fill.inputs[0])

                node_scale = builder.create_node("ShaderNodeCombineXYZ", (-1800, current_y))
                node_scale.inputs["X"].default_value = props.axis_label_size
                node_scale.inputs["Y"].default_value = props.axis_label_size
                node_scale.inputs["Z"].default_value = props.axis_label_size

                node_mul = builder.create_node("ShaderNodeMath", (-1800, current_y - 150))
                node_mul.operation = "MULTIPLY"
                node_mul.inputs[1].default_value = tick.fraction
                builder.link(sep_outputs[axis_idx], node_mul.inputs[0])

                node_pos = builder.create_node("ShaderNodeCombineXYZ", (-1600, current_y - 150))
                offset = AxisBuilder._OFFSET
                if axis_idx == 0:
                    builder.link(node_mul.outputs[0], node_pos.inputs["X"])
                    node_pos.inputs["Y"].default_value = -offset
                    node_pos.inputs["Z"].default_value = -offset
                elif axis_idx == 1:
                    node_pos.inputs["X"].default_value = -offset
                    builder.link(node_mul.outputs[0], node_pos.inputs["Y"])
                    node_pos.inputs["Z"].default_value = -offset
                else:
                    node_pos.inputs["X"].default_value = -offset
                    node_pos.inputs["Y"].default_value = -offset
                    builder.link(node_mul.outputs[0], node_pos.inputs["Z"])

                node_transform = builder.create_node("GeometryNodeTransform", (-1400, current_y))
                builder.link(node_fill.outputs[0], node_transform.inputs["Geometry"])
                builder.link(node_pos.outputs[0], node_transform.inputs["Translation"])
                builder.link(node_scale.outputs[0], node_transform.inputs["Scale"])

                tick_geos.append(node_transform.outputs[0])
                current_y -= 350

            if not tick_geos:
                continue

            if len(tick_geos) == 1:
                axis_geos.append(tick_geos[0])
            else:
                node_join = builder.create_node("GeometryNodeJoinGeometry", (-1200, current_y))
                for geo in tick_geos:
                    builder.link(geo, node_join.inputs[0])
                axis_geos.append(node_join.outputs[0])
                current_y -= 200

        if not axis_geos:
            return None, current_y

        if len(axis_geos) == 1:
            combined_geo = axis_geos[0]
        else:
            node_join_all = builder.create_node("GeometryNodeJoinGeometry", (-1000, current_y))
            for geo in axis_geos:
                builder.link(geo, node_join_all.inputs[0])
            combined_geo = node_join_all.outputs[0]
            current_y -= 200

        node_set_mat = builder.create_node("GeometryNodeSetMaterial", (-800, current_y))
        if mat:
            node_set_mat.inputs["Material"].default_value = mat
        builder.link(combined_geo, node_set_mat.inputs["Geometry"])

        return node_set_mat.outputs[0], current_y - 200
