import bpy  # type: ignore

from ..constants import ParamapperNames
from .builders import FilterBuilder, SpatialBuilder, VisualBuilder
from .materials import MaterialFactory
from .utils import GNTreeBuilder


class InfographicGenerator:
    def __init__(self, context, props):
        self.context = context
        self.props = props
        self.obj = context.active_object

    def _get_or_create_gn_tree(self, obj: bpy.types.Object) -> bpy.types.GeometryNodeTree:
        modifier = obj.modifiers.get(ParamapperNames.MODIFIER)
        if not modifier:
            modifier = obj.modifiers.new(name=ParamapperNames.MODIFIER, type="NODES")

        if modifier.node_group:
            bpy.data.node_groups.remove(modifier.node_group)

        ntree = bpy.data.node_groups.new(name=ParamapperNames.NODE_TREE, type="GeometryNodeTree")
        modifier.node_group = ntree
        return ntree

    def _create_base_nodes(self, builder: GNTreeBuilder, sanitized_csv_path: str):
        builder.tree.interface.new_socket(
            name="Geometry", in_out="INPUT", socket_type="NodeSocketGeometry"
        )
        node_input = builder.create_node("NodeGroupInput", (-600, 200))

        node_transform_base = builder.create_node("GeometryNodeTransform", (-400, 200))
        node_combine_scale = builder.create_node("ShaderNodeCombineXYZ", (-600, 350))
        node_combine_scale.name = ParamapperNames.NODE_SPREAD

        node_combine_scale.inputs["X"].default_value = self.props.bounds_size[0]
        node_combine_scale.inputs["Y"].default_value = self.props.bounds_size[1]
        node_combine_scale.inputs["Z"].default_value = self.props.bounds_size[2]

        node_bbox_scale = builder.create_node("ShaderNodeVectorMath", (-400, 350))
        node_bbox_scale.operation = "DIVIDE"
        node_bbox_scale.inputs[1].default_value = (10.0, 10.0, 10.0)

        builder.link(node_combine_scale.outputs[0], node_bbox_scale.inputs[0])
        builder.link(node_bbox_scale.outputs["Vector"], node_transform_base.inputs["Scale"])

        builder.link(node_input.outputs[0], node_transform_base.inputs["Geometry"])
        limits_geo = node_transform_base.outputs[0]

        node_output = builder.create_node("NodeGroupOutput", (800, 0))
        builder.tree.interface.new_socket(
            name="Geometry", in_out="OUTPUT", socket_type="NodeSocketGeometry"
        )

        node_csv = builder.create_node("GeometryNodeImportCSV", (-600, 0))
        node_csv.inputs["Path"].default_value = sanitized_csv_path

        node_set_pos = builder.create_node("GeometryNodeSetPosition", (200, 0))
        node_combine_xyz = builder.create_node("ShaderNodeCombineXYZ", (-200, 0))

        node_vec_math = builder.create_node("ShaderNodeVectorMath", (0, 0))

        node_vec_math.operation = "MULTIPLY"

        builder.link(node_csv.outputs["Point Cloud"], node_set_pos.inputs["Geometry"])
        builder.link(node_combine_xyz.outputs["Vector"], node_vec_math.inputs[0])

        builder.link(node_combine_scale.outputs[0], node_vec_math.inputs[1])

        builder.link(node_vec_math.outputs["Vector"], node_set_pos.inputs["Position"])

        return node_output, node_set_pos, node_combine_xyz, limits_geo

    def _join_and_output(self, builder: GNTreeBuilder, main_geo, text_geo, bbox_geo, node_output):
        geos = [main_geo]
        if text_geo:
            geos.append(text_geo)
        if bbox_geo:
            geos.append(bbox_geo)

        if len(geos) > 1:
            node_join = builder.create_node("GeometryNodeJoinGeometry", (2000, 0))
            for geo in geos:
                builder.link(geo, node_join.inputs[0])
            builder.link(node_join.outputs[0], node_output.inputs[0])
        else:
            builder.link(main_geo, node_output.inputs[0])

    def build(self, sanitized_csv_path: str):
        ntree = self._get_or_create_gn_tree(self.obj)

        builder = GNTreeBuilder(ntree)

        node_output, node_set_pos, node_combine_xyz, limits_geo = self._create_base_nodes(
            builder, sanitized_csv_path
        )

        current_y = SpatialBuilder.map_axes(self.props, builder, node_combine_xyz)

        base_points, current_y = FilterBuilder.apply_culling(
            self.props, builder, node_set_pos.outputs[0], current_y
        )
        base_points, current_y = FilterBuilder.apply_auto_fit(
            self.props, builder, base_points, current_y
        )
        base_points, scale_socket, current_y = SpatialBuilder.map_scale(
            self.props, builder, base_points, current_y
        )
        base_points, current_y = VisualBuilder.map_color(
            self.props, builder, base_points, current_y
        )

        mat = MaterialFactory.get_data_material(self.props, self.obj.name)
        mat_text = MaterialFactory.get_text_material(self.props, self.obj.name)

        if mat.name not in self.obj.data.materials:
            self.obj.data.materials.append(mat)

        if mat_text.name not in self.obj.data.materials:
            self.obj.data.materials.append(mat_text)

        mat_bbox = MaterialFactory.get_bbox_material(self.props, self.obj.name)
        if mat_bbox.name not in self.obj.data.materials:
            self.obj.data.materials.append(mat_bbox)

        main_geo = VisualBuilder.instantiate_models(
            self.props, builder, base_points, scale_socket, mat
        )
        text_geo = VisualBuilder.instantiate_labels(self.props, builder, base_points, mat_text)

        node_buildup = builder.create_node("ShaderNodeValue", (1200, 200))
        node_buildup.name = "ParamapperBuildUp"
        node_buildup.outputs[0].default_value = self.props.build_up

        node_count = builder.create_node("ShaderNodeValue", (1200, 0))
        node_count.outputs[0].default_value = float(self.props.parsed_row_count)

        node_index = builder.create_node("GeometryNodeInputIndex", (1200, -200))

        node_div = builder.create_node("ShaderNodeMath", (1400, -100))
        node_div.operation = "DIVIDE"
        builder.link(node_index.outputs[0], node_div.inputs[0])
        builder.link(node_count.outputs[0], node_div.inputs[1])

        node_mul1 = builder.create_node("ShaderNodeMath", (1400, -250))
        node_mul1.operation = "MULTIPLY"
        node_mul1.inputs[1].default_value = 0.95
        builder.link(node_div.outputs[0], node_mul1.inputs[0])

        node_sub = builder.create_node("ShaderNodeMath", (1600, 0))
        node_sub.operation = "SUBTRACT"
        builder.link(node_buildup.outputs[0], node_sub.inputs[0])
        builder.link(node_mul1.outputs[0], node_sub.inputs[1])

        node_mul2 = builder.create_node("ShaderNodeMath", (1600, -150))
        node_mul2.operation = "MULTIPLY"
        node_mul2.use_clamp = True
        node_mul2.inputs[1].default_value = 20.0
        builder.link(node_sub.outputs[0], node_mul2.inputs[0])

        node_combine = builder.create_node("ShaderNodeCombineXYZ", (1700, -100))
        builder.link(node_mul2.outputs[0], node_combine.inputs[0])
        builder.link(node_mul2.outputs[0], node_combine.inputs[1])
        builder.link(node_mul2.outputs[0], node_combine.inputs[2])

        node_scale_main = builder.create_node("GeometryNodeScaleInstances", (1800, 0))
        builder.link(main_geo, node_scale_main.inputs[0])
        builder.link(node_combine.outputs[0], node_scale_main.inputs["Scale"])
        main_geo = node_scale_main.outputs[0]

        node_radius_in = builder.create_node("GeometryNodeInputRadius", (1800, -150))
        node_radius_mul = builder.create_node("ShaderNodeMath", (1800, -250))
        node_radius_mul.operation = "MULTIPLY"
        builder.link(node_radius_in.outputs[0], node_radius_mul.inputs[0])
        builder.link(node_mul2.outputs[0], node_radius_mul.inputs[1])

        node_set_radius = builder.create_node("GeometryNodeSetPointRadius", (2000, 0))
        builder.link(main_geo, node_set_radius.inputs[0])
        builder.link(node_radius_mul.outputs[0], node_set_radius.inputs["Radius"])
        main_geo = node_set_radius.outputs[0]

        if text_geo:
            node_scale_text = builder.create_node("GeometryNodeScaleInstances", (1800, -400))
            builder.link(text_geo, node_scale_text.inputs[0])
            builder.link(node_combine.outputs[0], node_scale_text.inputs["Scale"])
            text_geo = node_scale_text.outputs[0]

        bbox_geo = VisualBuilder.add_bounding_box(self.props, builder, limits_geo, mat_bbox)

        self._join_and_output(builder, main_geo, text_geo, bbox_geo, node_output)

        try:
            bpy.ops.object.select_all(action="DESELECT")
            self.obj.select_set(True)
            self.context.view_layer.objects.active = self.obj
        except RuntimeError:
            pass
