import bpy  # type: ignore


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