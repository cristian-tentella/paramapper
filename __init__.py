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
from .callbacks import paramapper_frame_handler, paramapper_scale_sync_timer
from .properties import PARAMAPPER_PG_Settings

bl_info = {
    "name": "Paramapper",
    "author": "Cristian Tentella",
    "description": "",
    "blender": (5, 0, 0),
    "version": (0, 7, 0),
    "location": "View3D > Sidebar > Paramapper",
    "category": "3D View",
}

auto_load.init()


def register():
    auto_load.register()

    bpy.types.Object.paramapper = bpy.props.PointerProperty(type=PARAMAPPER_PG_Settings)

    if paramapper_frame_handler not in bpy.app.handlers.frame_change_post:
        bpy.app.handlers.frame_change_post.append(paramapper_frame_handler)
        
    if not bpy.app.timers.is_registered(paramapper_scale_sync_timer):
        bpy.app.timers.register(paramapper_scale_sync_timer)


def unregister():
    if paramapper_frame_handler in bpy.app.handlers.frame_change_post:
        bpy.app.handlers.frame_change_post.remove(paramapper_frame_handler)

    if bpy.app.timers.is_registered(paramapper_scale_sync_timer):
        bpy.app.timers.unregister(paramapper_scale_sync_timer)

    del bpy.types.Object.paramapper
    auto_load.unregister()
