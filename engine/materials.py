import bpy  # type: ignore

from ..constants import PM


def find_bsdf_and_set_color(mat, color):
    node_principled = next((n for n in mat.node_tree.nodes if n.type == "BSDF_PRINCIPLED"), None)
    if node_principled:
        node_principled.inputs["Base Color"].default_value = color


class MaterialFactory:
    @staticmethod
    def get_data_material(obj_name: str) -> bpy.types.Material:
        mat_name = f"{PM.Materials.DATA}_{obj_name}"
        mat = bpy.data.materials.get(mat_name)

        if not mat:
            mat = bpy.data.materials.new(name=mat_name)
            mat.use_nodes = True
            nodes = mat.node_tree.nodes
            links = mat.node_tree.links
            nodes.clear()

            node_output = nodes.new("ShaderNodeOutputMaterial")
            node_output.location = (300, 0)

            node_principled = nodes.new("ShaderNodeBsdfPrincipled")
            node_principled.location = (0, 0)

            node_ramp = nodes.new("ShaderNodeValToRGB")
            node_ramp.location = (-300, 0)
            node_ramp.name = PM.Nodes.COLOR_RAMP

            node_ramp.color_ramp.elements[0].color = (0.02, 0.1, 1.0, 1.0)
            node_ramp.color_ramp.elements[1].color = (1.0, 0.05, 0.05, 1.0)

            node_attr = nodes.new("ShaderNodeAttribute")
            node_attr.attribute_name = PM.Attributes.COLOR_MAP
            node_attr.attribute_type = "GEOMETRY"
            node_attr.location = (-500, 0)

            links.new(node_attr.outputs["Fac"], node_ramp.inputs["Fac"])
            links.new(node_ramp.outputs["Color"], node_principled.inputs["Base Color"])
            links.new(node_principled.outputs["BSDF"], node_output.inputs["Surface"])

        return mat

    @staticmethod
    def _get_material(material_name: str, color) -> bpy.types.Material:
        mat = bpy.data.materials.get(material_name)

        if not mat:
            mat = bpy.data.materials.new(name=material_name)
            mat.use_nodes = True

        find_bsdf_and_set_color(mat, color)

        return mat

    @staticmethod
    def get_text_material(text_color, obj_name: str) -> bpy.types.Material:
        return MaterialFactory._get_material(f"{PM.Materials.TEXT}_{obj_name}", text_color)

    @staticmethod
    def get_bbox_material(bbox_color, obj_name: str) -> bpy.types.Material:
        return MaterialFactory._get_material(f"{PM.Materials.BBOX}_{obj_name}", bbox_color)
