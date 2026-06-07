import bpy  # type: ignore

from .callbacks import (
    get_categorical_columns,
    get_filter_columns,
    get_numeric_columns,
    update_fast,
    update_fast_filters,
    update_infographic,
)


class PARAMAPPER_PG_ColumnMeta(bpy.types.PropertyGroup):
    name: bpy.props.StringProperty(name="Column Name")  # type: ignore

    data_type: bpy.props.EnumProperty(  # type: ignore
        name="Data Type",
        items=[
            ("NUMERIC", "Numeric", ""),
            ("CATEGORICAL", "Categorical", ""),
            ("DATETIME", "Datetime", ""),
        ],
        default="NUMERIC",
    )

    min_val: bpy.props.FloatProperty(name="Min Value", default=0.0)  # type: ignore
    max_val: bpy.props.FloatProperty(name="Max Value", default=0.0)  # type: ignore

    unique_tokens: bpy.props.StringProperty(name="Unique Tokens", default="")  # type: ignore


class PARAMAPPER_PG_FilterItem(bpy.types.PropertyGroup):
    column: bpy.props.EnumProperty(
        name="Column", items=get_filter_columns, update=update_infographic
    )  # type: ignore

    operation: bpy.props.EnumProperty(
        name="Operation",
        items=[
            ("GREATER_THAN", ">", "Greater Than"),
            ("LESS_THAN", "<", "Less Than"),
            ("EQUAL", "==", "Equal To"),
            ("NOT_EQUAL", "!=", "Not Equal"),
        ],
        default="GREATER_THAN",
        update=update_infographic,
    )  # type: ignore

    value: bpy.props.FloatProperty(name="Value", default=0.0, update=update_fast_filters)  # type: ignore


class PARAMAPPER_PG_Settings(bpy.types.PropertyGroup):
    def reset_to_defaults(self):
        self.filters.clear()
        self.active_filter_index = 0

        self.map_x = "NONE"
        self.map_y = "NONE"
        self.map_z = "NONE"
        self.map_scale = "NONE"
        self.map_color = "NONE"
        self.map_text = "NONE"

        self.show_bounding_box = True

    # Dataset

    dataset_path: bpy.props.StringProperty(  # type: ignore
        name="Dataset path",
        description="",
        default="",
    )

    last_parsed_path: bpy.props.StringProperty(default="")  # type: ignore

    dataset_has_been_parsed: bpy.props.BoolProperty(  # type: ignore
        name="Dataset has been parsed", default=False
    )

    # Global

    auto_update: bpy.props.BoolProperty(  # type: ignore
        name="Live Update",
        description="Automatically regenerate the infographic when a property changes",
        default=True,
    )

    global_scale: bpy.props.FloatProperty(  # type: ignore
        name="Global Scale", default=1.0, min=0.01, update=update_fast
    )

    # Filters

    filters: bpy.props.CollectionProperty(type=PARAMAPPER_PG_FilterItem)  # type: ignore
    active_filter_index: bpy.props.IntProperty(name="Active Filter Index", default=0)  # type: ignore

    auto_fit_bounds: bpy.props.BoolProperty(  # type: ignore
        name="Auto-Fit Bounds",
        description="Dynamically redistribute filtered data to occupy the entire bounding box",
        default=False,
        update=update_infographic,
    )

    # Bounding box

    show_bounding_box: bpy.props.BoolProperty(  # type: ignore
        name="Show Bounding Box",
        description="Display a wireframe bounding box around the dataset",
        default=True,
        update=update_infographic,
    )

    bounds_size: bpy.props.FloatVectorProperty(  # type: ignore
        name="Dimensions",
        subtype="XYZ",
        unit="LENGTH",
        default=(10.0, 10.0, 10.0),
        size=3,
        min=0.01,
        update=update_fast,
    )

    bbox_color: bpy.props.FloatVectorProperty(  # type: ignore
        name="Bounding Box Color",
        subtype="COLOR",
        default=(1.0, 1.0, 1.0, 1.0),
        size=4,
        min=0.0,
        max=1.0,
        update=update_fast,
    )

    # Columns

    parsed_row_count: bpy.props.IntProperty(  # type: ignore
        name="Row Count", default=0
    )

    columns: bpy.props.CollectionProperty(type=PARAMAPPER_PG_ColumnMeta)  # type: ignore

    # Mappings

    map_x: bpy.props.EnumProperty(
        name="X Axis", items=get_numeric_columns, update=update_infographic
    )  # type: ignore

    map_y: bpy.props.EnumProperty(
        name="Y Axis", items=get_numeric_columns, update=update_infographic
    )  # type: ignore

    map_z: bpy.props.EnumProperty(
        name="Z Axis", items=get_numeric_columns, update=update_infographic
    )  # type: ignore

    map_scale: bpy.props.EnumProperty(
        name="Scale", items=get_numeric_columns, update=update_infographic
    )  # type: ignore

    map_color: bpy.props.EnumProperty(  # type: ignore
        name="Color", items=get_numeric_columns, update=update_infographic
    )

    # Custom object

    instance_object: bpy.props.PointerProperty(  # type: ignore
        name="Instance Model", type=bpy.types.Object, update=update_infographic
    )

    override_material: bpy.props.BoolProperty(  # type: ignore
        name="Override Custom Material",
        description="Apply Paramapper's data colors instead of the model's original material",
        default=False,
        update=update_infographic,
    )

    # Text

    map_text: bpy.props.EnumProperty(
        name="Text Label", items=get_categorical_columns, update=update_infographic
    )  # type: ignore

    text_size: bpy.props.FloatProperty(  # type: ignore
        name="Text Size", default=1.0, min=0.01, update=update_fast
    )

    text_thickness: bpy.props.FloatProperty(  # type: ignore
        name="Text Thickness", default=0.0, min=0.0, update=update_infographic
    )

    text_offset: bpy.props.FloatVectorProperty(  # type: ignore
        name="Text Offset", subtype="XYZ", default=(0.0, 0.0, 1.5), size=3, update=update_fast
    )

    text_rotation: bpy.props.FloatVectorProperty(  # type: ignore
        name="Text Rotation", subtype="EULER", default=(0.0, 0.0, 0.0), size=3, update=update_fast
    )

    text_color: bpy.props.FloatVectorProperty(  # type: ignore
        name="Text Color",
        subtype="COLOR",
        default=(1.0, 1.0, 1.0, 1.0),
        size=4,
        min=0.0,
        max=1.0,
        update=update_fast,
    )
