import bpy  # type: ignore


class PARAMAPPER_OT_add_filter(bpy.types.Operator):
    bl_idname = "paramapper.add_filter"
    bl_label = "Add Filter"

    def execute(self, context):
        context.active_object.paramapper.filters.add()
        context.active_object.paramapper.active_filter_index = (
            len(context.active_object.paramapper.filters) - 1
        )

        if context.active_object.paramapper.auto_update:
            bpy.ops.paramapper.generate_nodes("INVOKE_DEFAULT")

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
