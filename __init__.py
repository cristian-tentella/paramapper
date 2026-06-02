# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful, but
# WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTIBILITY or FITNESS FOR A PARTICULAR PURPOSE. See the GNU
# General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program. If not, see <http://www.gnu.org/licenses/>.

import bpy  # type: ignore

from . import auto_load

bl_info = {
    "name": "Paramapper",
    "author": "Cristian Tentella",
    "description": "",
    "blender": (5, 0, 0),
    "version": (0, 3, 0),
    "location": "View3D > Sidebar > Paramapper",
    "category": "3D View",
}

auto_load.init()


def register():
    auto_load.register()

    from .properties import PARAMAPPER_PG_Settings

    bpy.types.Object.paramapper = bpy.props.PointerProperty(type=PARAMAPPER_PG_Settings)


def unregister():
    del bpy.types.Object.paramapper
    auto_load.unregister()
