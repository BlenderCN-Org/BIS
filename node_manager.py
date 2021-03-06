# Nikita Akimov
# interplanety@interplanety.org

import sys
import bpy
import os
import json
from . import cfg
from .node_node_group import NodeGroup
from .material import Material
from .node_tree import NodeTree
from .addon import Addon
from .WebRequests import WebRequest, WebAuthVars
from .bis_items import BISItems


class NodeManager:

    _material_limit_file_size = 26214400    # max zipped file with textures size (25 Mb)

    @staticmethod
    def items_from_bis(context, search_filter, page, update_preview=False):
        # get page of items list from BIS
        rez = None
        storage_subtype = Material.get_subtype(context)
        storage_subtype2 = Material.get_subtype2(context)
        request = WebRequest.send_request({
            'for': 'get_items',
            'search_filter': search_filter,
            'page': page,
            'storage': __class__.storage_type(context),
            'storage_subtype': storage_subtype,
            'storage_subtype2': storage_subtype2,
            'update_preview': update_preview
        })
        if request:
            request_rez = json.loads(request.text)
            rez = request_rez['stat']
            if request_rez['stat'] == 'OK':
                if not request_rez['data']['items']:
                    if WebAuthVars.userProStatus:
                        bpy.ops.message.messagebox('INVOKE_DEFAULT', message='Nothing found')
                    else:
                        bpy.ops.message.messagebox('INVOKE_DEFAULT', message='You do not have any active materials.\n \
                         Please log in your account on the BIS web site,\n \
                         Add some materials to the active palette,\n \
                         And press this button again.')
                preview_to_update = BISItems.update_previews_from_data(data=request_rez['data']['items'], list_name=__class__.storage_type(context))
                if preview_to_update:
                    request = WebRequest.send_request({
                        'for': 'update_previews',
                        'preview_list': preview_to_update,
                        'storage': __class__.storage_type(context),
                        'storage_subtype': storage_subtype,
                        'storage_subtype2': storage_subtype2
                    })
                    if request:
                        previews_update_rez = json.loads(request.text)
                        if previews_update_rez['stat'] == 'OK':
                            BISItems.update_previews_from_data(data=previews_update_rez['data']['items'], list_name=__class__.storage_type(context))
                BISItems.create_items_list(data=request_rez['data']['items'], list_name=__class__.storage_type(context))
                context.window_manager.bis_get_nodes_info_from_storage_vars.current_page = page
                context.window_manager.bis_get_nodes_info_from_storage_vars.current_page_status = request_rez['data']['status']
        return rez

    @staticmethod
    def from_bis(context, bis_item_id, item_type):
        # item_type = 'MATERIAL' or 'NODEGROUP'
        request_rez = {'stat': 'ERR', 'data': {'text': 'No Id', 'content': None}}
        if bis_item_id:
            subtype = Material.get_subtype(context=context)
            request = WebRequest.send_request({
                'for': 'get_item',
                'storage': __class__.storage_type(context=context),
                'storage_subtype': subtype,
                'storage_subtype2': Material.get_subtype2(context),
                'id': bis_item_id,
                'addon_version': Addon.current_version()
            })
            if request:
                request_rez = json.loads(request.text)
                if request_rez['stat'] == 'OK':
                    item_in_json = json.loads(request_rez['data']['item'])
                    if cfg.from_server_to_file:
                        with open(os.path.join(os.path.dirname(bpy.data.filepath), 'received_from_server.json'), 'w') as currentFile:
                            json.dump(item_in_json, currentFile, indent=4)
                    item_version = item_in_json['BIS_addon_version'] if 'BIS_addon_version' in item_in_json else Addon.node_group_first_version
                    if Addon.node_group_version_higher(item_version, Addon.current_version()):
                        bpy.ops.message.messagebox('INVOKE_DEFAULT', message='This material item was saved in higher BIS version and may not load correctly.\
                         Please download the last BIS add-on version!')
                    if item_in_json['type'] == 'Material':
                        # got Material (can be only object material)
                        if item_type == 'MATERIAL':
                            # use as Material
                            Material.from_json(context=context, material_json=item_in_json)
                        elif item_type == 'NODEGROUP':
                            # use as Node Group
                            active_node_tree = __class__.active_node_tree(context=context)
                            # NodeGroup.new(parent_node_tree=active_node_tree, name=item_in_json['name'])
                            node_group_json = {
                                'type': 'GROUP',
                                'bl_idname': 'ShaderNodeGroup' if active_node_tree.bl_idname == 'ShaderNodeTree' else 'CompositorNodeGroup',
                                'name': item_in_json['name'],
                                'label': '',
                                'hide': False,
                                'location': [0.0, 0.0],
                                'width': 300,
                                'height': 200,
                                'use_custom_color': False,
                                'color': [1.0, 1.0, 1.0],
                                'parent': '',
                                'inputs': [],
                                'outputs': [
                                    {
                                        'type': 'SHADER',
                                        'bl_idname': 'NodeSocketShader',
                                        'name': 'Surface'
                                    },
                                    {
                                        'type': 'SHADER',
                                        'bl_idname': 'NodeSocketShader',
                                        'name': 'Volume'
                                    },
                                    {
                                        'type': 'VECTOR',
                                        'bl_idname': 'NodeSocketVector',
                                        'name': 'Displacement',
                                        'default_value': [0.0, 0.0, 0.0]
                                    }
                                ],
                                'nodes': item_in_json['node_tree']['nodes'],
                                'links': item_in_json['node_tree']['links'],
                                'BIS_addon_version': Addon.current_version(),
                                'BIS_node_id': None
                            }
                            output_node = {
                                'type': 'GROUP_OUTPUT',
                                'bl_idname': 'NodeGroupOutput',
                                'name': 'Group Output',
                                'label': '',
                                'hide': False,
                                'location': [300.0, 0.0],
                                'width': 140.0,
                                'height': 100.0,
                                'use_custom_color': False,
                                'color': [1.0, 1.0, 1.0],
                                'parent': '',
                                'inputs': [
                                    {
                                        'type': 'SHADER',
                                        'bl_idname': 'NodeSocketShader',
                                        'name': 'Surface'
                                    },
                                    {
                                        'type': 'SHADER',
                                        'bl_idname': 'NodeSocketShader',
                                        'name': 'Volume'
                                    },
                                    {
                                        'type': 'VECTOR',
                                        'bl_idname': 'NodeSocketVector',
                                        'name': 'Displacement',
                                        'default_value': [0.0, 0.0, 0.0]
                                    }
                                ],
                                'outputs': [],
                                'is_active_output': True
                            }
                            node_group_json['nodes'].append(output_node)
                            input_node = {
                                'type': 'GROUP_INPUT',
                                'bl_idname': 'NodeGroupInput',
                                'name': 'Group Input',
                                'label': '',
                                'hide': False,
                                'location': [-300.0, 0.0],
                                'width': 140.0,
                                'height': 100.0,
                                'use_custom_color': False,
                                'color': [1.0, 1.0, 1.0],
                                'parent': '',
                                'inputs': [],
                                'outputs': []
                            }
                            node_group_json['nodes'].append(input_node)
                            node_group = NodeGroup.from_json(node_group_json=node_group_json, parent_node_tree=active_node_tree)
                            # create links from material output nodes to group output node
                            node_group_output_node = [node for node in node_group.node_tree.nodes if node.type == 'GROUP_OUTPUT'][0]
                            for link in node_group.node_tree.links:
                                if link.to_node.type == 'OUTPUT_MATERIAL':
                                    if link.to_socket.name == 'Surface':
                                        node_group.node_tree.links.new(link.from_socket, node_group_output_node.inputs['Surface'])
                                    elif link.to_socket.name == 'Volume':
                                        node_group.node_tree.links.new(link.from_socket, node_group_output_node.inputs['Volume'])
                                    elif link.to_socket.name == 'Displacement':
                                        node_group.node_tree.links.new(link.from_socket, node_group_output_node.inputs['Displacement'])
                            # remove material output nodes in node_group
                            for node in node_group.node_tree.nodes:
                                if node.type == 'OUTPUT_MATERIAL':
                                    node_group.node_tree.nodes.remove(node)
                    elif item_in_json['type'] == 'GROUP':
                        # got Node Group (can be object node group or compositor node group)
                        if item_type == 'NODEGROUP' or subtype == 'CompositorNodeTree':
                            # use as Node Group (for object material and compositor material)
                            if subtype == 'CompositorNodeTree' and not context.window.scene.use_nodes:
                                context.window.scene.use_nodes = True
                            if subtype == 'ShaderNodeTree':
                                if context.active_object and not context.active_object.active_material:
                                    Material.new(context=context)
                            active_node_tree = __class__.active_node_tree(context=context)
                            if item_in_json and active_node_tree:
                                nodegroup = NodeGroup.from_json(node_group_json=item_in_json, parent_node_tree=active_node_tree)
                                if nodegroup:
                                    nodegroup['bis_uid'] = bis_item_id
                        elif item_type == 'MATERIAL':
                            # use as Material (only for object material)
                            material = Material.new(context=context)
                            if material:
                                material.name = item_in_json['name']
                                Material.clear(material=material, exclude_output_nodes=True)
                                active_node_tree = __class__.active_node_tree(context=context)
                                nodegroup = NodeGroup.from_json(node_group_json=item_in_json, parent_node_tree=active_node_tree)
                                if nodegroup:
                                    nodegroup['bis_uid'] = bis_item_id
                                    # additional nodes and links
                                    # node group output
                                    shader_output = [i for i in nodegroup.outputs if i.type == 'SHADER' and 'volume' not in i.name.lower()]
                                    color_output = [i for i in nodegroup.outputs if i.type == 'RGBA']
                                    factor_output = [i for i in nodegroup.outputs if i.type == 'VALUE' and 'displacement' not in i.name.lower()]
                                    volume_output = [i for i in nodegroup.outputs if i.type == 'SHADER' and 'volume' in i.name.lower()]
                                    displacement_output = [i for i in nodegroup.outputs if i.type in ['VECTOR'] and i.name.lower() in ['displace', 'displacement', 'смещение']]
                                    normal_output = [i for i in nodegroup.outputs if i.type == 'VECTOR' and i.name.lower() not in ['displace', 'displacement', 'смещение']]
                                    # connect outputs
                                    if shader_output:
                                        active_node_tree.links.new(shader_output[0], active_node_tree.nodes['Material Output'].inputs['Surface'])
                                    elif color_output:
                                        diffuse_node = active_node_tree.nodes.new(type='ShaderNodeBsdfDiffuse')
                                        diffuse_node.location = (500.0, 0.0)
                                        active_node_tree.links.new(color_output[0], diffuse_node.inputs['Color'])
                                        active_node_tree.links.new(diffuse_node.outputs['BSDF'], active_node_tree.nodes['Material Output'].inputs['Surface'])
                                        if normal_output:
                                            active_node_tree.links.new(normal_output[0], diffuse_node.inputs['Normal'])
                                    elif factor_output:
                                        diffuse_node = active_node_tree.nodes.new(type='ShaderNodeBsdfDiffuse')
                                        diffuse_node.location = (500.0, 0.0)
                                        active_node_tree.links.new(factor_output[0], diffuse_node.inputs['Color'])
                                        active_node_tree.links.new(diffuse_node.outputs['BSDF'], active_node_tree.nodes['Material Output'].inputs['Surface'])
                                        if normal_output:
                                            active_node_tree.links.new(normal_output[0], diffuse_node.inputs['Normal'])
                                    if volume_output:
                                        active_node_tree.links.new(volume_output[0], active_node_tree.nodes['Material Output'].inputs['Volume'])
                                    if displacement_output:
                                        active_node_tree.links.new(displacement_output[0], active_node_tree.nodes['Material Output'].inputs['Displacement'])
                                    # connect inputs
                                    vector_input = [i for i in nodegroup.inputs if i.type == 'VECTOR' and i.name.lower() in ['vector']]
                                    if vector_input:
                                        texture_coordinates_node = active_node_tree.nodes.new(type='ShaderNodeTexCoord')
                                        texture_coordinates_node.location = (-200.0, 0.0)
                                        active_node_tree.links.new(texture_coordinates_node.outputs['UV'], vector_input[0])
            else:
                request_rez['data']['text'] = 'BIS server not request'
        return request_rez

    @staticmethod
    def to_bis(context, item, item_type, tags=''):
        # item = material or nodegroup
        # item_type = 'MATERIAL' or 'NODEGROUP'
        request_rez = {'stat': 'ERR', 'data': {'text': 'Error to save'}}
        item_json = None
        item_attachment = {}
        subtype = Material.get_subtype(context=context)
        if item:
            if item_type == 'NODEGROUP' or subtype == 'CompositorNodeTree':
                item_json = NodeGroup.to_json(nodegroup=item)
            elif item_type == 'MATERIAL':
                item_json = Material.to_json(context=context, material=item)
        if item_json and not __class__.is_procedural(material=item):
            # attachment file external items (textures,... etc)
            file_attachment = NodeTree.external_items(node_tree=item.node_tree)
            print(file_attachment)
            # if file_attachment:
            #     item_attachment['file_attachment'] = file_attachment
        if cfg.to_server_to_file:
            with open(os.path.join(os.path.dirname(bpy.data.filepath), 'send_to_server.json'), 'w') as currentFile:
                json.dump(item_json, currentFile, indent=4)
        # send to server
        if item_json and not cfg.no_sending_to_server:
            bis_links = list(__class__.get_bis_linked_items('bis_linked_item', item_json))
            request = WebRequest.send_request(
                data={
                'for': 'add_item',
                'item_body': json.dumps(item_json),
                'storage': __class__.storage_type(context=context),
                'storage_subtype': subtype,
                'storage_subtype2': Material.get_subtype2(context=context),
                'procedural': 1 if __class__.is_procedural(material=item) else 0,
                'engine': context.window.scene.render.engine,
                'bis_links': json.dumps(bis_links),
                'item_name': item_json['name'],
                'item_tags': tags.strip(),
                'addon_version': Addon.current_version()
                },
                files=item_attachment,
            )
            if request:
                request_rez = json.loads(request.text)
        if request_rez['stat'] == 'OK':
            item['bis_uid'] = request_rez['data']['id']
        return request_rez

    @staticmethod
    def update_in_bis(context, item, item_type):
        # item = material or nodegroup
        # item_type = 'MATERIAL' or 'NODEGROUP'
        request_rez = {'stat': 'ERR', 'data': {'text': 'Error to update'}}
        item_json = None
        subtype = Material.get_subtype(context=context)
        if item:
            if 'bis_uid' in item:
                if item_type == 'NODEGROUP' or subtype == 'CompositorNodeTree':
                    item_json = NodeGroup.to_json(nodegroup=item)
                elif item_type == 'MATERIAL':
                    item_json = Material.to_json(context=context, material=item)
            else:
                request_rez['data']['text'] = 'Save this Material item to the BIS first!'
        else:
            request_rez['data']['text'] = 'Undefined material item to update'
        if cfg.to_server_to_file:
            with open(os.path.join(os.path.dirname(bpy.data.filepath), 'send_to_server.json'), 'w') as currentFile:
                json.dump(item_json, currentFile, indent=4)
        # send to server
        if item_json and not cfg.no_sending_to_server:
            bis_links = list(__class__.get_bis_linked_items('bis_linked_item', item_json))
            request = WebRequest.send_request(data={
                'for': 'update_item',
                'item_body': json.dumps(item_json),
                'storage': __class__.storage_type(context=context),
                'storage_subtype': subtype,
                'storage_subtype2': Material.get_subtype2(context=context),
                'procedural': 1 if __class__.is_procedural(material=item) else 0,
                'engine': context.window.scene.render.engine,
                'bis_links': json.dumps(bis_links),
                'item_id': item['bis_uid'],
                'item_name': item_json['name'],
                'addon_version': Addon.current_version()
            })
            if request:
                request_rez = json.loads(request.text)
        return request_rez

    @staticmethod
    def storage_type(context):
        # return context.area.spaces.active.type
        return 'NODE_EDITOR'

    @staticmethod
    def active_node_tree(context):
        # returns currently opened node tree in NODE_EDITOR window
        active_node_tree = None
        subtype = Material.get_subtype(context=context)
        if subtype == 'ShaderNodeTree':
            subtype2 = Material.get_subtype2(context=context)
            if subtype2 == 'OBJECT':
                if context.active_object and context.active_object.active_material:
                    active_node_tree = context.active_object.active_material.node_tree
            elif subtype2 == 'WORLD':
                active_node_tree = context.scene.world.node_tree
        elif subtype == 'CompositorNodeTree':
            if context.window.scene.use_nodes:
                active_node_tree = context.area.spaces.active.node_tree
        if active_node_tree and NodeTree.has_node_groups(active_node_tree) and hasattr(context.space_data, 'path'):
            for i in range(len(context.space_data.path) - 1):
                active_node_tree = active_node_tree.nodes.active.node_tree
        return active_node_tree

    @staticmethod
    def active_node(context):
        # returns currently active node in NODE_EDITOR window
        active_node = None
        active_node_tree = __class__.active_node_tree(context=context)
        if active_node_tree:
            active_node = active_node_tree.nodes.active
        return active_node

    @staticmethod
    def active_material(context):
        # returns currently active material in NODE_EDITOR window
        active_material = None
        if context.active_object and context.active_object.active_material:
            active_material = context.active_object.active_material
        return active_material

    @staticmethod
    def is_procedural(material):
        # check if material (nodegroup) is fully procedural
        rez = True
        for node in material.node_tree.nodes:
            if node.type == 'GROUP':
                rez = __class__.is_procedural(node)
                if not rez:
                    break
            elif node.type == 'TEX_IMAGE':
                rez = False
                break
            elif node.type == 'SCRIPT' and node.mode == 'EXTERNAL':
                rez = False
                break
        return rez

    @staticmethod
    def cpu_render_required(material):
        # check if material (nodegroup) required only CPU render
        rez = False
        for node in material.node_tree.nodes:
            if node.type == 'GROUP':
                rez = __class__.cpu_render_required(node)
                if rez:
                    break
            elif node.type == 'SCRIPT':
                rez = True
                break
        return rez

    @staticmethod
    # returns generator to crate list with all linked items (texts, ...) to current item (nodegroup)
    def get_bis_linked_items(key, nodegroup_in_json):
        for k, v in nodegroup_in_json.items():
            if k == key:
                yield v
            elif isinstance(v, dict):
                for result in __class__.get_bis_linked_items(key, v):
                    yield result
            elif isinstance(v, list):
                for d in v:
                    if isinstance(d, dict):
                        for result in __class__.get_bis_linked_items(key, d):
                            yield result
