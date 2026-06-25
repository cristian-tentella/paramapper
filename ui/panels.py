import bpy  # type: ignore

from ..constants import PM


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


class PARAMAPPER_PT_parsed_base:
    @classmethod
    def poll(cls, context):
        obj = context.active_object
        return obj and obj.type == "MESH" and obj.paramapper.dataset_has_been_parsed


class PARAMAPPER_PT_mapping(PARAMAPPER_PT_parsed_base, bpy.types.Panel):
    bl_idname = "PARAMAPPER_PT_mapping"
    bl_parent_id = "PARAMAPPER_PT_main"
    bl_label = "Mapping"
    bl_space_type = "VIEW_3D"
    bl_region_type = "UI"
    bl_order = 20

    def draw(self, context):
        layout = self.layout
        layout.use_property_split = True
        layout.use_property_decorate = False

        props = context.active_object.paramapper
        obj = context.active_object

        def draw_axis_with_range(axis_prop, label):
            col_name = getattr(props, axis_prop)
            layout.prop(props, axis_prop, text=label)

            if col_name != "NONE":
                col_meta = props.columns.get(col_name)
                if col_meta and col_meta.data_type == "NUMERIC":
                    hint = layout.row()
                    hint.active = False
                    hint.alignment = "RIGHT"
                    hint.label(text=f"{col_meta.min_val:.2f} ↔ {col_meta.max_val:.2f}")

        draw_axis_with_range("map_x", "X")
        draw_axis_with_range("map_y", "Y")
        draw_axis_with_range("map_z", "Z")

        layout.separator()

        layout.prop(props, "map_scale", text="Scale")

        layout.separator()

        layout.prop(props, "map_text", text="Text")
        if props.map_text != "NONE":
            box_text = layout.box()
            box_text.prop(props, "text_size", text="Size")
            box_text.prop(props, "text_thickness", text="Thickness")
            box_text.prop(props, "text_offset", text="Offset")
            box_text.prop(props, "text_rotation", text="Rotation")
            box_text.prop(props, "text_color", text="Color")

        layout.separator()

        show_color_ui = not props.instance_object or props.override_material
        if show_color_ui:
            layout.prop(props, "map_color", text="Color")

            if props.map_color != "NONE":
                mat_name = f"{PM.Materials.DATA}_{obj.name}"
                mat = bpy.data.materials.get(mat_name)
                node_ramp = (
                    mat.node_tree.nodes.get(PM.Nodes.COLOR_RAMP) if mat and mat.use_nodes else None
                )

                if node_ramp:
                    layout.template_color_ramp(node_ramp, "color_ramp", expand=False)
                else:
                    layout.label(text="Generate to edit Color Ramp", icon="INFO")


class PARAMAPPER_PT_filters(PARAMAPPER_PT_parsed_base, bpy.types.Panel):
    bl_idname = "PARAMAPPER_PT_filters"
    bl_parent_id = "PARAMAPPER_PT_main"
    bl_label = "Data Filtering"
    bl_space_type = "VIEW_3D"
    bl_region_type = "UI"
    bl_order = 30

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


class PARAMAPPER_PT_bounds(PARAMAPPER_PT_parsed_base, bpy.types.Panel):
    bl_idname = "PARAMAPPER_PT_bounds"
    bl_parent_id = "PARAMAPPER_PT_main"
    bl_label = "Bounds"
    bl_space_type = "VIEW_3D"
    bl_region_type = "UI"
    bl_order = 40

    def draw(self, context):
        layout = self.layout
        layout.use_property_split = True
        layout.use_property_decorate = False

        props = context.active_object.paramapper

        layout.prop(props, "bounds_size", text="Dimensions")
        layout.prop(props, "global_scale", text="Items Base Size")

        layout.separator()

        layout.prop(props, "auto_fit_bounds", text="Auto-Fit Filtered Data")

        layout.separator()

        layout.prop(props, "show_bounding_box")
        if props.show_bounding_box:
            layout.prop(props, "bbox_color", text="Color")

        layout.separator()

        layout.prop(props, "show_axis_labels")
        if props.show_axis_labels:
            col = layout.column(align=True)
            col.prop(props, "axis_label_count", text="Tick Count")
            col.prop(props, "axis_label_size", text="Size")


class PARAMAPPER_PT_visuals(PARAMAPPER_PT_parsed_base, bpy.types.Panel):
    bl_idname = "PARAMAPPER_PT_visuals"
    bl_parent_id = "PARAMAPPER_PT_main"
    bl_label = "Style"
    bl_space_type = "VIEW_3D"
    bl_region_type = "UI"
    bl_order = 50

    def draw(self, context):
        layout = self.layout
        layout.use_property_split = True
        layout.use_property_decorate = False

        props = context.active_object.paramapper

        layout.prop(props, "build_up", text="Build-up", icon="TIME")

        layout.separator()

        layout.prop(props, "instance_object", text="Instance Model")
        if props.instance_object:
            layout.prop(props, "override_material")
            hint = layout.row()
            hint.active = False
            hint.label(text="Set origin to geometry for correct positioning", icon="INFO")
