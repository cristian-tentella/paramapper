import os
import traceback

import bpy  # type: ignore
from bpy_extras.io_utils import ImportHelper  # type: ignore
from bpy_extras.object_utils import object_data_add  # type: ignore

from .constants import ParamapperNames
from .generator import InfographicGenerator
from .parsers import get_parser


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


class PARAMAPPER_OT_create_object(bpy.types.Operator):
    bl_idname = "paramapper.create_object"
    bl_label = "Create Infographic Object"
    bl_options = {"REGISTER", "UNDO"}

    def execute(self, context):
        mesh_data = bpy.data.meshes.new(ParamapperNames.CONTAINER_MESH)

        verts = [
            (0.0, 0.0, 0.0),
            (10.0, 0.0, 0.0),
            (10.0, 10.0, 0.0),
            (0.0, 10.0, 0.0),
            (0.0, 0.0, 10.0),
            (10.0, 0.0, 10.0),
            (10.0, 10.0, 10.0),
            (0.0, 10.0, 10.0),
        ]
        edges = [
            (0, 1),
            (1, 2),
            (2, 3),
            (3, 0),
            (4, 5),
            (5, 6),
            (6, 7),
            (7, 4),
            (0, 4),
            (1, 5),
            (2, 6),
            (3, 7),
        ]

        mesh_data.from_pydata(verts, edges, [])

        object_data_add(context, mesh_data, name=ParamapperNames.CONTAINER_OBJ)

        self.report({"INFO"}, "Infographic Object created successfully!")
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
                props.filters.clear()
                props.active_filter_index = 0

                props.map_x = "NONE"
                props.map_y = "NONE"
                props.map_z = "NONE"
                props.map_scale = "NONE"
                props.map_color = "NONE"
                props.map_text = "NONE"

                props.show_bounding_box = True

                props.last_parsed_path = props.dataset_path

            props.columns.clear()
            for col_name, data in metadata.items():
                new_col = props.columns.add()
                new_col.name = col_name
                new_col.data_type = data["type"]
                new_col.min_val = data["min"] if data["min"] is not None else 0.0
                new_col.max_val = data["max"] if data["max"] is not None else 0.0
                new_col.unique_tokens = data["tokens"] if data["tokens"] is not None else ""

        except Exception as e:
            self.report({"ERROR"}, f"Dataset parsing error: {str(e)}")
            return {"CANCELLED"}

        props.dataset_has_been_parsed = True
        self.report({"INFO"}, f"Read {len(metadata)} valid columns")

        return {"FINISHED"}


class PARAMAPPER_OT_generate_nodes(bpy.types.Operator):
    bl_idname = "paramapper.generate_nodes"
    bl_label = "Generate Infographic"
    bl_options = {"REGISTER", "UNDO"}

    def execute(self, context: bpy.types.Context) -> set[str]:
        obj = context.active_object
        if not obj or obj.type != "MESH":
            return {"CANCELLED"}

        props = obj.paramapper

        abs_path = bpy.path.abspath(props.dataset_path)
        if not os.path.exists(abs_path):
            self.report({"WARNING"}, "Source CSV file missing or moved. Please load it again.")
            props.dataset_has_been_parsed = False
            return {"CANCELLED"}

        try:
            base, ext = os.path.splitext(abs_path)
            sanitized_path = f"{base}_bl51_ready{ext}"

            parser = get_parser(abs_path)
            parser.create_sanitized_copy(props.columns, sanitized_path)

            generator = InfographicGenerator(context, props)
            generator.build(sanitized_csv_path=sanitized_path)

            return {"FINISHED"}
        except Exception as e:
            error_type = type(e).__name__
            error_msg = str(e)

            print("\n" + "=" * 50)
            print(f"--- PARAMAPPER TRACEBACK DETAILED ERROR ({error_type}) ---")
            traceback.print_exc()
            print("=" * 50 + "\n")

            self.report(
                {"ERROR"}, f"Paramapper Error [{error_type}]: {error_msg} (Check System Console)"
            )
            return {"CANCELLED"}
