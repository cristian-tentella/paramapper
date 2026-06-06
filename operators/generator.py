import os
import traceback

import bpy  # type: ignore
from bpy_extras.object_utils import object_data_add  # type: ignore

from ..constants import ParamapperNames
from ..engine.generator import InfographicGenerator
from ..io.parsers import get_parser  # type: ignore


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
