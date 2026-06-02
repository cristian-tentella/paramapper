import bpy # type: ignore
from .constants import ParamapperNames

class PARAMAPPER_PT_main(bpy.types.Panel):
    bl_idname = 'PARAMAPPER_PT_main'
    bl_category = 'Paramapper'
    bl_label = 'Paramapper'
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    
    def draw(self, context):
        layout = self.layout
        obj = context.active_object
        
        layout.operator("paramapper.create_object", text="Create Infographic Object", icon='PLUS')

        if not obj or obj.type != 'MESH':
            layout.separator()
            box = layout.box()
            box.label(text="Select or create an Infographic to start.", icon='INFO')
            return
            
        props = obj.paramapper
        
        if props.dataset_has_been_parsed:
            layout.separator()
            row_actions = layout.row(align=True)
            row_actions.prop(props, "auto_update", text="Live", toggle=True, icon='RESTRICT_VIEW_OFF' if props.auto_update else 'RESTRICT_VIEW_ON')
            row_actions.operator("paramapper.generate_nodes", text="Generate Infographic", icon='PLAY')


class PARAMAPPER_PT_dataset(bpy.types.Panel):
    bl_idname = 'PARAMAPPER_PT_dataset'
    bl_parent_id = 'PARAMAPPER_PT_main'
    bl_label = 'Dataset'
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_order = 10

    @classmethod
    def poll(cls, context):
        obj = context.active_object
        return obj and obj.type == 'MESH'

    def draw(self, context):
        layout = self.layout
        props = context.active_object.paramapper
        
        row_path = layout.row(align=True)
        row_path.prop(props, 'dataset_path', text='')
        row_path.operator('paramapper.browse_datasets', icon='FILEBROWSER', text='')
        
        icon_parse = "FILE_REFRESH" if props.dataset_has_been_parsed else "FILE_SCRIPT"
        layout.operator("paramapper.parse_dataset", text="Parse Dataset", icon=icon_parse)

        if props.dataset_has_been_parsed:
            col_info = layout.column(align=True)
            col_info.label(text=f"Data Points: {props.parsed_row_count:,}", icon='MESH_DATA')
            col_info.label(text=f"Valid Columns: {len(props.columns)}", icon='SPREADSHEET')


class PARAMAPPER_PT_spatial(bpy.types.Panel):
    bl_idname = 'PARAMAPPER_PT_spatial'
    bl_parent_id = 'PARAMAPPER_PT_main'
    bl_label = 'Spatial Mapping'
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_order = 20

    @classmethod
    def poll(cls, context):
        obj = context.active_object
        return obj and obj.type == 'MESH' and obj.paramapper.dataset_has_been_parsed

    def draw(self, context):
        layout = self.layout
        props = context.active_object.paramapper
        
        col_axes = layout.column(align=True)
        col_axes.prop(props, "map_x", text="X Axis")
        col_axes.prop(props, "map_y", text="Y Axis")
        col_axes.prop(props, "map_z", text="Z Axis")
        
        layout.separator()
        
        col_mult = layout.column(align=True)
        col_mult.prop(props, "spread_vector", text="Spread")
        col_mult.prop(props, "global_scale", text="Items Base Size")


class PARAMAPPER_PT_visuals(bpy.types.Panel):
    bl_idname = 'PARAMAPPER_PT_visuals'
    bl_parent_id = 'PARAMAPPER_PT_main'
    bl_label = 'Visual Features'
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_order = 30

    @classmethod
    def poll(cls, context):
        obj = context.active_object
        return obj and obj.type == 'MESH' and obj.paramapper.dataset_has_been_parsed

    def draw(self, context):
        layout = self.layout
        props = context.active_object.paramapper
        obj = context.active_object
        
        col_model = layout.column(align=True)
        col_model.prop(props, "instance_object", text="Instance Model")
        if props.instance_object:
            col_model.prop(props, "override_material")
            
        layout.separator()
        
        col_mapping = layout.column(align=True)
        col_mapping.prop(props, "map_scale", text="Map Scale To")
        col_mapping.prop(props, "map_text", text="Map Text To")
        
        layout.separator()
        
        box_bbox = layout.box()
        box_bbox.prop(props, "show_bounding_box")
        if props.show_bounding_box:
            box_bbox.prop(props, "bbox_color", text="Color")
        
        if props.map_text != 'NONE':
            box_text = layout.box()
            box_text.prop(props, "text_size", text="Size")
            box_text.prop(props, "text_thickness", text="Thickness")
            box_text.prop(props, "text_offset", text="Offset")
            box_text.prop(props, "text_rotation", text="Rotation")
            box_text.prop(props, "text_color", text="Color")
        
        layout.separator()
        
        show_color_ui = (not props.instance_object) or (props.instance_object and props.override_material)
        
        if show_color_ui:
            layout.prop(props, "map_color", text="Color")

            if props.map_color != 'NONE':
                mat_name = f"{ParamapperNames.MATERIAL}_{obj.name}"
                mat = bpy.data.materials.get(mat_name)
                if mat and mat.use_nodes:
                    node_ramp = mat.node_tree.nodes.get(ParamapperNames.COLOR_RAMP_NODE)
                    if node_ramp:
                        box_ramp = layout.box()
                        box_ramp.template_color_ramp(node_ramp, "color_ramp", expand=True)
                    else:
                        layout.label(text="Generate to edit Color Ramp", icon='INFO')
                else:
                    layout.label(text="Generate to edit Color Ramp", icon='INFO')