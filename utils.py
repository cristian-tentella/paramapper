import bpy # type: ignore

class GNTreeBuilder:
    def __init__(self, node_tree: bpy.types.GeometryNodeTree):
        self.tree = node_tree
        self.nodes = node_tree.nodes
        self.links = node_tree.links
    
    def create_node(self, id: str, location: tuple[float, float], **kwargs) -> bpy.types.Node:
        node = self.nodes.new(id)
        node.location = location
        
        for key, value in kwargs.items():
            if hasattr(node, key):
                setattr(node, key, value)
        
        return node

    def link(self, from_socket: bpy.types.NodeSocket, to_socket: bpy.types.NodeSocket):
        self.links.new(from_socket, to_socket)
    
    def create_mapped_attribute(self, col_name: str,
                                from_min: float, from_max: float,
                                to_min: float, to_max: float,
                                location: tuple[float, float]) -> bpy.types.NodeSocket:
        node_attr = self.create_node('GeometryNodeInputNamedAttribute', location, data_type='FLOAT')
        node_attr.inputs['Name'].default_value = col_name

        x, y = location
        node_map = self.create_node('ShaderNodeMapRange', (x + 200, y))
        node_map.inputs['From Min'].default_value = from_min
        node_map.inputs['From Max'].default_value = from_max
        node_map.inputs['To Min'].default_value = to_min
        node_map.inputs['To Max'].default_value = to_max
        
        self.link(node_attr.outputs['Attribute'], node_map.inputs['Value'])

        return node_map.outputs['Result']
        