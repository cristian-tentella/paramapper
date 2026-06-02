import bpy # type: ignore

from .constants import ParamapperNames

class MaterialFactory:
    @staticmethod
    def get_data_material(props, obj_name: str) -> bpy.types.Material:
        mat_name = f"{ParamapperNames.MATERIAL}_{obj_name}" 
        mat = bpy.data.materials.get(mat_name)

        if not mat:
            mat = bpy.data.materials.new(name=mat_name)
            mat.use_nodes = True
            nodes = mat.node_tree.nodes
            links = mat.node_tree.links
            nodes.clear()

            node_output = nodes.new('ShaderNodeOutputMaterial')
            node_output.location = (300, 0)

            node_principled = nodes.new('ShaderNodeBsdfPrincipled')
            node_principled.location = (0, 0)
 
            node_ramp = nodes.new('ShaderNodeValToRGB')
            node_ramp.location = (-300, 0)
            node_ramp.name = ParamapperNames.COLOR_RAMP_NODE
 
            node_ramp.color_ramp.elements[0].color = (0.02, 0.1, 1.0, 1.0)
            node_ramp.color_ramp.elements[1].color = (1.0, 0.05, 0.05, 1.0)

            node_attr = nodes.new('ShaderNodeAttribute')
            node_attr.attribute_name = ParamapperNames.COLOR_MAP_ATTR
            node_attr.attribute_type = 'GEOMETRY'
            node_attr.location = (-500, 0)
 
            links.new(node_attr.outputs['Fac'], node_ramp.inputs['Fac'])
            links.new(node_ramp.outputs['Color'], node_principled.inputs['Base Color'])
            links.new(node_principled.outputs['BSDF'], node_output.inputs['Surface'])
 
        nodes = mat.node_tree.nodes
        node_ramp = nodes.get(ParamapperNames.COLOR_RAMP_NODE)

        if not node_ramp:
            for node in nodes:
                if node.type == 'VALTORGB':
                    node_ramp = node
                    node_ramp.name = ParamapperNames.COLOR_RAMP_NODE
                    break

        return mat

    @staticmethod
    def get_text_material(props, obj_name: str) -> bpy.types.Material:
        mat_name = f"{ParamapperNames.TEXT_MATERIAL}_{obj_name}" 
        mat = bpy.data.materials.get(mat_name)
        
        if not mat:
            mat = bpy.data.materials.new(name=mat_name)
            mat.use_nodes = True
            
        if mat.use_nodes:
            node_principled = next((n for n in mat.node_tree.nodes if n.type == 'BSDF_PRINCIPLED'), None)
            if node_principled:
                node_principled.inputs['Base Color'].default_value = props.text_color
        return mat

    @staticmethod
    def get_bbox_material(props, obj_name: str) -> bpy.types.Material:
        mat_name = f"{ParamapperNames.BBOX_MATERIAL}_{obj_name}"
        mat = bpy.data.materials.get(mat_name)
        
        if not mat:
            mat = bpy.data.materials.new(name=mat_name)
            mat.use_nodes = True

        if mat.use_nodes:
            node_principled = next((n for n in mat.node_tree.nodes if n.type == 'BSDF_PRINCIPLED'), None)
            if node_principled:
                node_principled.inputs['Base Color'].default_value = props.bbox_color

        return mat