import bpy  # type: ignore


class PARAMAPPER_OT_add_filter(bpy.types.Operator):
    bl_idname = "paramapper.add_filter"
    bl_label = "Add Filter"
    bl_options = {"REGISTER", "UNDO"}

    def execute(self, context):
        obj = context.active_object
        if not obj or obj.type != "MESH":
            self.report({"WARNING"}, "Select a Mesh Object first")
            return {"CANCELLED"}

        props = obj.paramapper

        props.filters.add()
        props.active_filter_index = len(props.filters) - 1

        if props.auto_update:
            bpy.ops.paramapper.generate_nodes("INVOKE_DEFAULT")

        return {"FINISHED"}


class PARAMAPPER_OT_remove_filter(bpy.types.Operator):
    bl_idname = "paramapper.remove_filter"
    bl_label = "Remove Filter"
    bl_options = {"REGISTER", "UNDO"}

    def execute(self, context):
        obj = context.active_object
        if not obj or obj.type != "MESH":
            self.report({"WARNING"}, "Select a Mesh Object first")
            return {"CANCELLED"}

        props = obj.paramapper

        if props.filters:
            props.filters.remove(props.active_filter_index)
            props.active_filter_index = max(0, props.active_filter_index - 1)

            if props.auto_update:
                bpy.ops.paramapper.generate_nodes("INVOKE_DEFAULT")

        return {"FINISHED"}
