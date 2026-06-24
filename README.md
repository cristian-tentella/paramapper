# Paramapper

Paramapper is a Blender add-on for procedural data visualization. It reads a CSV file, infers each column's type (numeric, datetime, or categorical), and builds a Geometry Nodes tree on a mesh object that maps columns to X/Y/Z position, instance scale, color, and text labels over a point cloud. Mappings, bounds, filters, colors, and a build-up animation are driven by per-object properties in a sidebar panel and update live as you change them.

## Requirements

- Blender 5.0.0 or newer. The extension uses the `GeometryNodeImportCSV` node and Geometry Nodes features from Blender 5.0.
- No external dependencies to install. `numpy` is used at parse time and ships with Blender's bundled Python.

## How it works

State lives per-object under `obj.paramapper`, so multiple infographics can exist in one scene. On parse, the CSV is classified and a numeric-only copy is written to Blender's temp directory (categoricals become integer indices, datetimes become float timestamps) because the CSV import node only handles numbers. Generating builds a Geometry Nodes modifier named `ParamapperGraph`. Property changes either patch named nodes in place (bounds, scale, colors, text transform, filter values) or, for changes that alter the node graph's topology, trigger a rebuild on a background timer.
