import bpy  # type: ignore

from .constants import ParamapperNames


class PARAMAPPER_PT_main(bpy.types.Panel):
    bl_idname = "PARAMAPPER_PT_main"
    bl_category = "Paramapper"
    bl_label = "Paramapper"
    bl_space_type = "VIEW_3D"
    bl_region_type = "UI"

    def draw(self, context):
        layout = self.layout
        obj = context.active_object

        layout.operator("paramapper.create_object", text="Create Infographic Object", icon="PLUS")

        if not obj or obj.type != "MESH":
            layout.separator()
            box = layout.box()
            box.label(text="Select or create an Infographic to start.", icon="INFO")
            return

        props = obj.paramapper

        if props.dataset_has_been_parsed:
            layout.separator()
            row_actions = layout.row(align=True)
            row_actions.prop(
                props,
                "auto_update",
                text="Live",
                toggle=True,
                icon="RESTRICT_VIEW_OFF" if props.auto_update else "RESTRICT_VIEW_ON",
            )
            row_actions.operator(
                "paramapper.generate_nodes", text="Generate Infographic", icon="PLAY"
            )


class PARAMAPPER_PT_dataset(bpy.types.Panel):
    bl_idname = "PARAMAPPER_PT_dataset"
    bl_parent_id = "PARAMAPPER_PT_main"
    bl_label = "Dataset"
    bl_space_type = "VIEW_3D"
    bl_region_type = "UI"
    bl_order = 10

    @classmethod
    def poll(cls, context):
        obj = context.active_object
        return obj and obj.type == "MESH"

    def draw(self, context):
        layout = self.layout
        props = context.active_object.paramapper

        row_path = layout.row(align=True)
        row_path.prop(props, "dataset_path", text="")
        row_path.operator("paramapper.browse_datasets", icon="FILEBROWSER", text="")

        icon_parse = "FILE_REFRESH" if props.dataset_has_been_parsed else "FILE_SCRIPT"
        layout.operator("paramapper.parse_dataset", text="Parse Dataset", icon=icon_parse)

        if props.dataset_has_been_parsed:
            col_info = layout.column(align=True)
            col_info.label(text=f"Data Points: {props.parsed_row_count:,}", icon="MESH_DATA")
            col_info.label(text=f"Valid Columns: {len(props.columns)}", icon="SPREADSHEET")


class PARAMAPPER_PT_spatial(bpy.types.Panel):
    bl_idname = "PARAMAPPER_PT_spatial"
    bl_parent_id = "PARAMAPPER_PT_main"
    bl_label = "Spatial Mapping"
    bl_space_type = "VIEW_3D"
    bl_region_type = "UI"
    bl_order = 20

    @classmethod
    def poll(cls, context):
        obj = context.active_object
        return obj and obj.type == "MESH" and obj.paramapper.dataset_has_been_parsed

    def draw(self, context):
        layout = self.layout
        props = context.active_object.paramapper

        col_axes = layout.column(align=True)

        def draw_axis_with_range(axis_prop, label):
            col_name = getattr(props, axis_prop)

            split = col_axes.split(factor=0.7)
            split.prop(props, axis_prop, text=label)

            if col_name != "NONE":
                col_meta = props.columns.get(col_name)
                if col_meta and col_meta.data_type == "NUMERIC":
                    info_row = split.row()
                    info_row.active = False
                    info_row.alignment = "RIGHT"
                    info_row.label(text=f"[{col_meta.min_val:.2f} ↔ {col_meta.max_val:.2f}]")

        draw_axis_with_range("map_x", "X")
        col_axes.separator(factor=0.5)
        draw_axis_with_range("map_y", "Y")
        col_axes.separator(factor=0.5)
        draw_axis_with_range("map_z", "Z")

        layout.separator()
        
        col_fit = layout.column(align=True)
        col_fit.prop(props, "auto_fit_bounds", text="Auto-Fit Filtered Data", icon="ARROW_LEFTRIGHT")

        layout.separator()

        col_mult = layout.column(align=True)
        col_mult.prop(props, "bounds_size", text="Dimensions")
        col_mult.prop(props, "global_scale", text="Items Base Size")


class PARAMAPPER_UL_filter_list(bpy.types.UIList):
    def draw_item(self, context, layout, data, item, icon, active_data, active_propname, index):
        col = layout.column(align=True)

        row = col.row(align=True)
        split = row.split(factor=0.5, align=True)
        split.prop(item, "column", text="", icon="EYEDROPPER")

        sub_row = split.row(align=True)

        sub_split = sub_row.split(factor=0.35, align=True)
        sub_split.prop(item, "operation", text="")
        sub_split.prop(item, "value", text="")

        if item.column != "NONE":
            obj = context.active_object
            col_meta = obj.paramapper.columns.get(item.column)
            if col_meta and col_meta.data_type == "NUMERIC":
                info_row = col.row()
                info_row.active = False
                info_row.alignment = "RIGHT"
                info_row.label(
                    text=f"Range: {col_meta.min_val:.2f} ↔ {col_meta.max_val:.2f}", icon="INFO"
                )


class PARAMAPPER_OT_add_filter(bpy.types.Operator):
    bl_idname = "paramapper.add_filter"
    bl_label = "Add Filter"

    def execute(self, context):
        context.active_object.paramapper.filters.add()
        context.active_object.paramapper.active_filter_index = (
            len(context.active_object.paramapper.filters) - 1
        )
        return {"FINISHED"}


class PARAMAPPER_OT_remove_filter(bpy.types.Operator):
    bl_idname = "paramapper.remove_filter"
    bl_label = "Remove Filter"

    def execute(self, context):
        props = context.active_object.paramapper
        if len(props.filters) > 0:
            props.filters.remove(props.active_filter_index)
            props.active_filter_index = max(0, props.active_filter_index - 1)
            bpy.ops.paramapper.generate_nodes("INVOKE_DEFAULT")
        return {"FINISHED"}


class PARAMAPPER_PT_filters(bpy.types.Panel):
    bl_idname = "PARAMAPPER_PT_filters"
    bl_parent_id = "PARAMAPPER_PT_main"
    bl_label = "Data Filtering"
    bl_space_type = "VIEW_3D"
    bl_region_type = "UI"
    bl_order = 30

    @classmethod
    def poll(cls, context):
        obj = context.active_object
        return obj and obj.paramapper.dataset_has_been_parsed

    def draw(self, context):
        layout = self.layout
        props = context.active_object.paramapper

        row = layout.row()
        row.template_list(
            "PARAMAPPER_UL_filter_list", "", props, "filters", props, "active_filter_index", rows=3
        )

        col = row.column(align=True)
        col.operator("paramapper.add_filter", icon="ADD", text="")
        col.operator("paramapper.remove_filter", icon="REMOVE", text="")


class PARAMAPPER_PT_visuals(bpy.types.Panel):
    bl_idname = "PARAMAPPER_PT_visuals"
    bl_parent_id = "PARAMAPPER_PT_main"
    bl_label = "Visual Features"
    bl_space_type = "VIEW_3D"
    bl_region_type = "UI"
    bl_order = 40

    @classmethod
    def poll(cls, context):
        obj = context.active_object
        return obj and obj.type == "MESH" and obj.paramapper.dataset_has_been_parsed

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

        if props.map_text != "NONE":
            box_text = layout.box()
            box_text.prop(props, "text_size", text="Size")
            box_text.prop(props, "text_thickness", text="Thickness")
            box_text.prop(props, "text_offset", text="Offset")
            box_text.prop(props, "text_rotation", text="Rotation")
            box_text.prop(props, "text_color", text="Color")

        layout.separator()

        show_color_ui = (not props.instance_object) or (
            props.instance_object and props.override_material
        )

        if show_color_ui:
            layout.prop(props, "map_color", text="Color")

            if props.map_color != "NONE":
                mat_name = f"{ParamapperNames.MATERIAL}_{obj.name}"
                mat = bpy.data.materials.get(mat_name)
                if mat and mat.use_nodes:
                    node_ramp = mat.node_tree.nodes.get(ParamapperNames.COLOR_RAMP_NODE)
                    if node_ramp:
                        box_ramp = layout.box()
                        box_ramp.template_color_ramp(node_ramp, "color_ramp", expand=True)
                    else:
                        layout.label(text="Generate to edit Color Ramp", icon="INFO")
                else:
                    layout.label(text="Generate to edit Color Ramp", icon="INFO")
