import bpy  # type: ignore
from bpy_extras.io_utils import ImportHelper  # type: ignore

from ..io.parsers import get_parser


class PARAMAPPER_OT_browse_datasets(bpy.types.Operator, ImportHelper):
    bl_idname = "paramapper.browse_datasets"
    bl_label = "Select dataset"
    bl_options = {"REGISTER", "UNDO"}

    filter_glob: bpy.props.StringProperty(  # type: ignore
        default="*.csv", options={"HIDDEN"}, maxlen=255
    )

    def execute(self, context):
        obj = context.active_object
        if obj and obj.type == "MESH":
            obj.paramapper.dataset_path = self.filepath

        return {"FINISHED"}


class PARAMAPPER_OT_parse_dataset(bpy.types.Operator):
    bl_idname = "paramapper.parse_dataset"
    bl_label = "Parse dataset"
    bl_options = {"REGISTER", "UNDO"}

    def execute(self, context):
        obj = context.active_object
        if not obj or obj.type != "MESH":
            self.report({"WARNING"}, "Select a Mesh Object first")
            return {"CANCELLED"}

        props = obj.paramapper

        if not props.dataset_path:
            self.report({"ERROR"}, "Invalid dataset file")
            return {"CANCELLED"}

        abs_path: str = bpy.path.abspath(props.dataset_path)

        try:
            parser = get_parser(abs_path)
            parser.validate_file()
            metadata = parser.extract_metadata()

            props.parsed_row_count = parser.row_count

            if props.dataset_path != props.last_parsed_path:
                props.reset_to_defaults()
                props.last_parsed_path = props.dataset_path

            props.columns.clear()
            for col_name, data in metadata.items():
                new_col = props.columns.add()
                new_col.name = col_name

                new_col.data_type = data.data_type
                new_col.min_val = data.min_val if data.min_val is not None else 0.0
                new_col.max_val = data.max_val if data.max_val is not None else 0.0
                new_col.unique_tokens = data.tokens if data.tokens is not None else ""

        except Exception as e:
            self.report({"ERROR"}, f"Dataset parsing error: {str(e)}")
            return {"CANCELLED"}

        props.dataset_has_been_parsed = True
        self.report({"INFO"}, f"Read {len(metadata)} valid columns")

        return {"FINISHED"}
