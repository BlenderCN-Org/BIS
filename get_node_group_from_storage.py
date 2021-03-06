# Nikita Akimov
# interplanety@interplanety.org

import bpy
from bpy.props import IntProperty
from bpy.utils import register_class, unregister_class
from bpy.types import Operator
from .node_manager import NodeManager


class GetNodeGroupFromStorage(Operator):
    bl_idname = 'bis.get_nodegroup_from_storage'
    bl_label = 'BIS_GetFromStorage'
    bl_description = 'Get nodegroup from common part of BIS'
    bl_options = {'REGISTER', 'UNDO'}

    node_group_id: IntProperty(
        name='node_group_id',
        default=0
    )

    def execute(self, context):
        rez = {"stat": "ERR", "data": {"text": "No Material To Get"}}
        if self.node_group_id:
            rez = NodeManager.from_bis(context=context,
                                       bis_item_id=self.node_group_id,
                                       item_type=context.preferences.addons[__package__].preferences.use_node_group_as
                                       )
        if rez['stat'] != 'OK':
            bpy.ops.message.messagebox('INVOKE_DEFAULT', message=rez['stat'] + ': ' + rez['data']['text'])
        return {'FINISHED'}


def register():
    register_class(GetNodeGroupFromStorage)


def unregister():
    unregister_class(GetNodeGroupFromStorage)
