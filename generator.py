import csv
import os
import bpy # type: ignore

from .constants import ParamapperNames
from .materials import MaterialFactory
from .utils import GNTreeBuilder

class InfographicGenerator:
    def __init__(self, context, props):
        self.context = context
        self.props = props
        self.obj = context.active_object

    def _sanitize_csv(self) -> str:
        abs_path = bpy.path.abspath(self.props.dataset_path)
        base, ext = os.path.splitext(abs_path)
        sanitized_path = f"{base}_bl51_ready{ext}"
        
        token_maps = {}
        for col in self.props.columns:
            if col.data_type == 'CATEGORICAL' and col.unique_tokens:
                tokens = col.unique_tokens.split('\n')
                token_maps[col.name] = {t: str(idx) for idx, t in enumerate(tokens)}
                
        with open(abs_path, mode='r', encoding='utf-8') as f_in, \
             open(sanitized_path, mode='w', newline='', encoding='utf-8') as f_out:
            
            reader = csv.DictReader(f_in)
            writer = csv.DictWriter(f_out, fieldnames=reader.fieldnames)
            writer.writeheader()
            
            for row in reader:
                for col_name, mapping in token_maps.items():
                    if col_name in row:
                        row[col_name] = mapping.get(row[col_name].strip(), "0")
                writer.writerow(row)
                
        return sanitized_path

    def _get_or_create_gn_tree(self, obj: bpy.types.Object) -> bpy.types.GeometryNodeTree:
        modifier = obj.modifiers.get(ParamapperNames.MODIFIER)
        if not modifier:
            modifier = obj.modifiers.new(name=ParamapperNames.MODIFIER, type='NODES')
        
        if modifier.node_group:
            bpy.data.node_groups.remove(modifier.node_group)
        
        ntree = bpy.data.node_groups.new(name=ParamapperNames.NODE_TREE, type='GeometryNodeTree')
        modifier.node_group = ntree
        return ntree

    def _create_base_nodes(self, builder: GNTreeBuilder, sanitized_csv_path: str):
        builder.tree.interface.new_socket(name="Geometry", in_out='INPUT', socket_type='NodeSocketGeometry')
        node_input = builder.create_node('NodeGroupInput', (-600, 200))
        
        node_transform_base = builder.create_node('GeometryNodeTransform', (-400, 200))
        node_combine_scale = builder.create_node('ShaderNodeCombineXYZ', (-600, 350))
        node_combine_scale.name = ParamapperNames.NODE_SPREAD
        
        node_combine_scale.inputs['X'].default_value = self.props.spread_vector[0]
        node_combine_scale.inputs['Y'].default_value = self.props.spread_vector[1]
        node_combine_scale.inputs['Z'].default_value = self.props.spread_vector[2]
        
        builder.link(node_combine_scale.outputs[0], node_transform_base.inputs['Scale'])
        builder.link(node_input.outputs[0], node_transform_base.inputs['Geometry'])
        limits_geo = node_transform_base.outputs[0]

        node_output = builder.create_node('NodeGroupOutput', (800, 0))
        builder.tree.interface.new_socket(name="Geometry", in_out='OUTPUT', socket_type='NodeSocketGeometry')
        
        node_csv = builder.create_node('GeometryNodeImportCSV', (-600, 0))
        node_csv.inputs['Path'].default_value = sanitized_csv_path
        
        node_set_pos = builder.create_node('GeometryNodeSetPosition', (200, 0))
        node_combine_xyz = builder.create_node('ShaderNodeCombineXYZ', (-200, 0))
        
        node_vec_math = builder.create_node('ShaderNodeVectorMath', (0, 0))
        
        node_vec_math.operation = 'MULTIPLY'

        builder.link(node_csv.outputs['Point Cloud'], node_set_pos.inputs['Geometry'])
        builder.link(node_combine_xyz.outputs['Vector'], node_vec_math.inputs[0])
        
        builder.link(node_combine_scale.outputs[0], node_vec_math.inputs[1])
        
        builder.link(node_vec_math.outputs['Vector'], node_set_pos.inputs['Position'])
        
        return node_output, node_set_pos, node_combine_xyz, limits_geo

    def _map_axes(self, builder: GNTreeBuilder, node_combine_xyz) -> int:
        axis_mappings = {'X': self.props.map_x, 'Y': self.props.map_y, 'Z': self.props.map_z}
        current_y = 0
        
        for axis, col_name in axis_mappings.items():
            if col_name == 'NONE':
                continue
                
            col_meta = self.props.columns.get(col_name)
            if not col_meta:
                continue
            
            mapped_socket = builder.create_mapped_attribute(
                col_name,
                from_min=col_meta.min_val,
                from_max=col_meta.max_val,
                to_min=0.0,
                to_max=10.0,
                location=(-400, current_y)
            )
            builder.link(mapped_socket, node_combine_xyz.inputs[axis])
            current_y -= 250
            
        return current_y

    def _map_scale(self, builder: GNTreeBuilder, current_geo, current_y: int):
        scale_socket = None
        
        if self.props.map_scale != 'NONE':
            col_meta = self.props.columns.get(self.props.map_scale)
            if col_meta:
                scale_socket = builder.create_mapped_attribute(
                    col_name=self.props.map_scale,
                    from_min=col_meta.min_val,
                    from_max=col_meta.max_val,
                    to_min=0.1,
                    to_max=1.0,
                    location=(-400, current_y)
                )
                node_set_radius = builder.create_node('GeometryNodeSetPointRadius', (400, 0))
                builder.link(scale_socket, node_set_radius.inputs['Radius'])
                builder.link(current_geo, node_set_radius.inputs[0])
                
                current_geo = node_set_radius.outputs[0]
                current_y -= 250
                
        return current_geo, scale_socket, current_y

    def _map_color(self, builder: GNTreeBuilder, current_geo, current_y: int):
        if getattr(self.props, 'map_color', 'NONE') != 'NONE':
            col_meta = self.props.columns.get(self.props.map_color)
            if col_meta:
                color_socket = builder.create_mapped_attribute(
                    col_name=self.props.map_color,
                    from_min=col_meta.min_val,
                    from_max=col_meta.max_val,
                    to_min=0.0,
                    to_max=1.0,
                    location=(-400, current_y)
                )
                
                node_store = builder.create_node('GeometryNodeStoreNamedAttribute', (400, current_y))
                node_store.data_type = 'FLOAT'
                node_store.domain = 'POINT'
                node_store.inputs['Name'].default_value = ParamapperNames.COLOR_MAP_ATTR
                
                builder.link(current_geo, node_store.inputs['Geometry'])
                builder.link(color_socket, node_store.inputs['Value'])
                
                return node_store.outputs[0], current_y - 250
                
        return current_geo, current_y

    def _add_bounding_box(self, builder: GNTreeBuilder, limits_geo, mat_bbox):
        if not self.props.show_bounding_box:
            return None

        node_m2c = builder.create_node('GeometryNodeMeshToCurve', (1200, 200))
        builder.link(limits_geo, node_m2c.inputs[0])

        node_c2m = builder.create_node('GeometryNodeCurveToMesh', (1400, 200))
        node_circle = builder.create_node('GeometryNodeCurvePrimitiveCircle', (1200, 50))
        node_circle.inputs['Radius'].default_value = 0.02
        node_circle.inputs['Resolution'].default_value = 4 
        
        builder.link(node_m2c.outputs[0], node_c2m.inputs['Curve'])
        builder.link(node_circle.outputs[0], node_c2m.inputs['Profile Curve'])

        node_mat = builder.create_node('GeometryNodeSetMaterial', (1600, 200))
        if mat_bbox:
            node_mat.inputs['Material'].default_value = mat_bbox
            
        builder.link(node_c2m.outputs[0], node_mat.inputs['Geometry'])
        return node_mat.outputs[0]

    def _instantiate_models(self, builder: GNTreeBuilder, base_points, scale_socket, mat):
        node_global_vec = builder.create_node('ShaderNodeCombineXYZ', (200, -100))
        node_global_vec.name = ParamapperNames.NODE_GLOBAL_SCALE
        node_global_vec.inputs['X'].default_value = self.props.global_scale
        node_global_vec.inputs['Y'].default_value = self.props.global_scale
        node_global_vec.inputs['Z'].default_value = self.props.global_scale

        node_base_reduction = builder.create_node('ShaderNodeVectorMath', (400, -100))
        node_base_reduction.operation = 'MULTIPLY'
        node_base_reduction.inputs[1].default_value = (0.2, 0.2, 0.2)
        
        builder.link(node_global_vec.outputs[0], node_base_reduction.inputs[0])

        if self.props.instance_object:
            node_src = builder.create_node('GeometryNodeObjectInfo', (400, 200))
            node_src.inputs['Object'].default_value = self.props.instance_object
            node_src.transform_space = 'ORIGINAL'
            instance_socket = node_src.outputs['Geometry']
            
            node_inst = builder.create_node('GeometryNodeInstanceOnPoints', (800, 100))
            builder.link(base_points, node_inst.inputs['Points'])
            builder.link(instance_socket, node_inst.inputs['Instance'])
            
            if scale_socket:
                node_math_scale = builder.create_node('ShaderNodeVectorMath', (600, -100))
                node_math_scale.operation = 'MULTIPLY'
                builder.link(scale_socket, node_math_scale.inputs[0])
                builder.link(node_base_reduction.outputs[0], node_math_scale.inputs[1])
                builder.link(node_math_scale.outputs['Vector'], node_inst.inputs['Scale'])
            else:
                builder.link(node_base_reduction.outputs[0], node_inst.inputs['Scale'])

            current_geo = node_inst.outputs[0]
            apply_data_material = self.props.override_material
            
        else:
            node_sep_xyz = builder.create_node('ShaderNodeSeparateXYZ', (600, -200))
            builder.link(node_base_reduction.outputs[0], node_sep_xyz.inputs[0])
            
            node_radius_math = builder.create_node('ShaderNodeMath', (800, -100))
            node_radius_math.operation = 'MULTIPLY'
            
            if scale_socket:
                builder.link(scale_socket, node_radius_math.inputs[0])
                builder.link(node_sep_xyz.outputs['X'], node_radius_math.inputs[1])
            else:
                node_radius_math.inputs[0].default_value = 1.0
                builder.link(node_sep_xyz.outputs['X'], node_radius_math.inputs[1])
                
            node_set_radius = builder.create_node('GeometryNodeSetPointRadius', (1000, 100))
            builder.link(base_points, node_set_radius.inputs['Points']) 
            builder.link(node_radius_math.outputs['Value'], node_set_radius.inputs['Radius'])
            
            current_geo = node_set_radius.outputs[0]
            apply_data_material = True

        if apply_data_material:
            node_mat = builder.create_node('GeometryNodeSetMaterial', (1200, 100))
            if mat:
                node_mat.inputs['Material'].default_value = mat
            builder.link(current_geo, node_mat.inputs['Geometry'])
            return node_mat.outputs[0]
        else:
            return current_geo
    
    def _build_text_instances(self, builder: GNTreeBuilder, tokens: list[str]) -> bpy.types.NodeSocket:
        node_geo_to_inst = builder.create_node('GeometryNodeGeometryToInstance', (800, -400))
        
        for i, token in enumerate(tokens):
            node_str = builder.create_node('GeometryNodeStringToCurves', (0, -400 - (i * 250)))
            node_str.inputs['String'].default_value = token
            
            node_fill = builder.create_node('GeometryNodeFillCurve', (200, -400 - (i * 250)))
            builder.link(node_str.outputs[0], node_fill.inputs[0])
            
            if self.props.text_thickness > 0.0:
                node_extrude = builder.create_node('GeometryNodeExtrudeMesh', (400, -400 - (i * 250)))
                node_extrude.inputs['Offset Scale'].default_value = self.props.text_thickness
                
                node_flip = builder.create_node('GeometryNodeFlipFaces', (400, -550 - (i * 250)))
                node_join_cap = builder.create_node('GeometryNodeJoinGeometry', (600, -400 - (i * 250)))
                
                builder.link(node_fill.outputs[0], node_flip.inputs[0])
                builder.link(node_flip.outputs[0], node_join_cap.inputs[0])
                builder.link(node_fill.outputs[0], node_extrude.inputs['Mesh'])
                builder.link(node_extrude.outputs['Mesh'], node_join_cap.inputs[0])
                
                builder.link(node_join_cap.outputs[0], node_geo_to_inst.inputs[0])
            else:
                builder.link(node_fill.outputs[0], node_geo_to_inst.inputs[0])
                
        return node_geo_to_inst.outputs[0]

    def _instantiate_labels(self, builder: GNTreeBuilder, base_points, mat_text):
        if self.props.map_text == 'NONE':
            return None
            
        col_meta = self.props.columns.get(self.props.map_text)
        if not col_meta or not col_meta.unique_tokens:
            return None
            
        tokens = col_meta.unique_tokens.split('\n')
        
        instances_socket = self._build_text_instances(builder, tokens)
        
        node_text_attr = builder.create_node('GeometryNodeInputNamedAttribute', (800, -600), data_type='FLOAT')
        node_text_attr.inputs['Name'].default_value = self.props.map_text
        
        node_inst = builder.create_node('GeometryNodeInstanceOnPoints', (1000, -300))
        node_inst.inputs['Pick Instance'].default_value = True
        
        node_text_scale = builder.create_node('ShaderNodeCombineXYZ', (800, -750))
        node_text_scale.name = ParamapperNames.NODE_TEXT_SIZE
        node_text_scale.inputs['X'].default_value = self.props.text_size
        node_text_scale.inputs['Y'].default_value = self.props.text_size
        node_text_scale.inputs['Z'].default_value = self.props.text_size
        
        builder.link(node_text_scale.outputs[0], node_inst.inputs['Scale'])
        builder.link(base_points, node_inst.inputs['Points'])
        builder.link(instances_socket, node_inst.inputs['Instance'])
        builder.link(node_text_attr.outputs[0], node_inst.inputs['Instance Index'])
        
        node_translate = builder.create_node('GeometryNodeTranslateInstances', (1200, -300))
        node_trans_vec = builder.create_node('ShaderNodeCombineXYZ', (1000, -500))
        node_trans_vec.name = ParamapperNames.NODE_TEXT_OFFSET
        node_trans_vec.inputs['X'].default_value = self.props.text_offset[0]
        node_trans_vec.inputs['Y'].default_value = self.props.text_offset[1]
        node_trans_vec.inputs['Z'].default_value = self.props.text_offset[2]
        
        builder.link(node_inst.outputs[0], node_translate.inputs['Instances'])
        builder.link(node_trans_vec.outputs[0], node_translate.inputs['Translation'])
        
        node_rotate = builder.create_node('GeometryNodeRotateInstances', (1400, -300))
        node_rot_vec = builder.create_node('ShaderNodeCombineXYZ', (1200, -500))
        node_rot_vec.name = ParamapperNames.NODE_TEXT_ROTATION
        node_rot_vec.inputs['X'].default_value = self.props.text_rotation[0]
        node_rot_vec.inputs['Y'].default_value = self.props.text_rotation[1]
        node_rot_vec.inputs['Z'].default_value = self.props.text_rotation[2]
        
        builder.link(node_translate.outputs[0], node_rotate.inputs['Instances'])
        builder.link(node_rot_vec.outputs[0], node_rotate.inputs['Rotation'])
        
        node_set_mat = builder.create_node('GeometryNodeSetMaterial', (1600, -300))
        if mat_text:
            node_set_mat.inputs['Material'].default_value = mat_text
            
        builder.link(node_rotate.outputs[0], node_set_mat.inputs['Geometry'])
        
        return node_set_mat.outputs[0]
    
    def _join_and_output(self, builder: GNTreeBuilder, main_geo, text_geo, bbox_geo, node_output):
        geos = [main_geo]
        if text_geo: geos.append(text_geo)
        if bbox_geo: geos.append(bbox_geo)
            
        if len(geos) > 1:
            node_join = builder.create_node('GeometryNodeJoinGeometry', (2000, 0))
            for geo in geos:
                builder.link(geo, node_join.inputs[0]) 
            builder.link(node_join.outputs[0], node_output.inputs[0])
        else:
            builder.link(main_geo, node_output.inputs[0])
    
    def build(self, sanitized_csv_path: str):
        ntree = self._get_or_create_gn_tree(self.obj)
        
        builder = GNTreeBuilder(ntree)

        node_output, node_set_pos, node_combine_xyz, limits_geo = self._create_base_nodes(builder, sanitized_csv_path)
        
        current_y = self._map_axes(builder, node_combine_xyz)
        base_points, scale_socket, current_y = self._map_scale(builder, node_set_pos.outputs[0], current_y)
        
        base_points, current_y = self._map_color(builder, base_points, current_y)
        
        mat = MaterialFactory.get_data_material(self.props, self.obj.name)
        mat_text = MaterialFactory.get_text_material(self.props, self.obj.name)
        
        if mat.name not in self.obj.data.materials:
            self.obj.data.materials.append(mat)
            
        if mat_text.name not in self.obj.data.materials:
            self.obj.data.materials.append(mat_text)
        
        mat_bbox = MaterialFactory.get_bbox_material(self.props, self.obj.name)
        if mat_bbox.name not in self.obj.data.materials:
            self.obj.data.materials.append(mat_bbox)
        
        main_geo = self._instantiate_models(builder, base_points, scale_socket, mat)
        text_geo = self._instantiate_labels(builder, base_points, mat_text)
        
        bbox_geo = self._add_bounding_box(builder, limits_geo, mat_bbox)
       
        self._join_and_output(builder, main_geo, text_geo, bbox_geo, node_output)

        try:
            bpy.ops.object.select_all(action='DESELECT')
            self.obj.select_set(True)
            self.context.view_layer.objects.active = self.obj
        except RuntimeError:
            pass