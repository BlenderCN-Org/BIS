# Nikita Akimov
# interplanety@interplanety.org

import bpy
from bpy.props import BoolProperty
from bpy.types import Operator
from bpy.utils import register_class, unregister_class
from . import cfg
from .node_manager import NodeManager


class BISUpdateNodegroup(Operator):
    bl_idname = 'bis.update_nodegroup_in_storage'
    bl_label = 'Update nodegroup'
    bl_description = 'Update nodegroup in the BIS'
    bl_options = {'REGISTER', 'UNDO'}

    show_message: BoolProperty(
        default=True
    )

    def execute(self, context):
        request_rez = {"stat": "ERR", "data": {"text": "Undefined material item to update"}}
        item_to_update = None
        if context.preferences.addons[__package__].preferences.use_node_group_as == 'NODEGROUP':
            active_node = NodeManager.active_node(context=context)
            if active_node and active_node.type == 'GROUP':
                item_to_update = active_node  # save active node group
            else:
                request_rez['data']['text'] = 'No selected Node Group'
        elif context.preferences.addons[__package__].preferences.use_node_group_as == 'MATERIAL':
            active_material = NodeManager.active_material(context=context)
            if active_material:
                item_to_update = active_material  # save active material
            else:
                request_rez['data']['text'] = 'No material to save'
        if item_to_update:
            request_rez = NodeManager.update_in_bis(context=context,
                                                    item=item_to_update,
                                                    item_type=context.preferences.addons[__package__].preferences.use_node_group_as
                                                    )
        if request_rez['stat'] != 'OK':
            if cfg.show_debug_err:
                print(request_rez['stat'] + ': ' + request_rez['data']['text'])
        if self.show_message:
            bpy.ops.message.messagebox('INVOKE_DEFAULT', message=request_rez['stat'] + ': ' + request_rez['data']['text'])
        return {'FINISHED'}

    def draw(self, context):
        layout = self.layout
        layout.separator()
        layout.label(text='Update current material item in the BIS?')
        layout.separator()

    def invoke(self, context, event):
        return context.window_manager.invoke_props_dialog(self, width=400)


def register():
    register_class(BISUpdateNodegroup)


def unregister():
    unregister_class(BISUpdateNodegroup)
