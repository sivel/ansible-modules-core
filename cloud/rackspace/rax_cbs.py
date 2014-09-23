#!/usr/bin/python
# This file is part of Ansible
#
# Ansible is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# Ansible is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with Ansible.  If not, see <http://www.gnu.org/licenses/>.

# This is a DOCUMENTATION stub specific to this module, it extends
# a documentation fragment located in ansible.utils.module_docs_fragments
DOCUMENTATION = '''
---
module: rax_cbs
short_description: Manipulate Rackspace Cloud Block Storage Volumes
description:
     - Manipulate Rackspace Cloud Block Storage Volumes
version_added: 1.6
options:
  description:
    description:
      - Description to give the volume being created
    default: null
  image:
    description:
      - image to use for bootable volumes. Can be an C(id), C(human_id) or
        C(name)
    default: null
    version_added: 1.8
  meta:
    description:
      - A hash of metadata to associate with the volume
    default: null
  name:
    description:
      - Name to give the volume being created
    default: null
    required: true
  size:
    description:
      - Size of the volume to create in Gigabytes
    default: 100
    required: true
  snapshot_id:
    description:
      - The id of the snapshot to create the volume from
    default: null
  state:
    description:
      - Indicate desired state of the resource
    choices:
      - present
      - absent
    default: present
    required: true
  volume_type:
    description:
      - Type of the volume being created
    choices:
      - SATA
      - SSD
    default: SATA
    required: true
  wait:
    description:
      - wait for the volume to be in state 'available' before returning
    default: "no"
    choices:
      - "yes"
      - "no"
  wait_timeout:
    description:
      - how long before wait gives up, in seconds
    default: 300
author: Christopher H. Laco, Matt Martz
extends_documentation_fragment: rackspace.openstack
'''

EXAMPLES = '''
- name: Build a Block Storage Volume
  gather_facts: False
  hosts: local
  connection: local
  tasks:
    - name: Storage volume create request
      local_action:
        module: rax_cbs
        credentials: ~/.raxpub
        name: my-volume
        description: My Volume
        volume_type: SSD
        size: 150
        region: DFW
        wait: yes
        state: present
        meta:
          app: my-cool-app
      register: my_volume
'''

try:
    import pyrax
    HAS_PYRAX = True
except ImportError:
    HAS_PYRAX = False


def cloud_block_storage(module, state, name, description, meta, size,
                        snapshot_id, volume_type, wait, wait_timeout,
                        image):
    for arg in (state, name, size, volume_type):
        if not arg:
            module.fail_json(msg='%s is required for rax_cbs' % arg)

    if size < 100:
        module.fail_json(msg='"size" must be greater than or equal to 100')

    changed = False
    volume = None
    instance = {}

    cbs = pyrax.cloud_blockstorage

    if cbs is None:
        module.fail_json(msg='Failed to instantiate client. This '
                             'typically indicates an invalid region or an '
                             'incorrectly capitalized region name.')

    if image:
        image = rax_find_image(module, pyrax, image)

    volume = rax_find_volume(module, pyrax, name)

    if state == 'present':
        if not volume:
            try:
                volume = cbs.create(name, size=size, volume_type=volume_type,
                                    description=description,
                                    metadata=meta,
                                    snapshot_id=snapshot_id, image=image)
                changed = True
            except Exception, e:
                module.fail_json(msg='%s' % e.message)
            else:
                if wait:
                    attempts = wait_timeout / 5
                    pyrax.utils.wait_for_build(volume, interval=5,
                                               attempts=attempts)

        volume.get()
        instance = rax_to_dict(volume)

        result = dict(changed=changed, volume=instance)

        if volume.status == 'error':
            result['msg'] = '%s failed to build' % volume.id
        elif wait and volume.status not in VOLUME_STATUS:
            result['msg'] = 'Timeout waiting on %s' % volume.id

        if 'msg' in result:
            module.fail_json(**result)
        else:
            module.exit_json(**result)

    elif state == 'absent':
        if volume:
            try:
                volume.delete()
                changed = True
            except Exception, e:
                module.fail_json(msg='%s' % e.message)

    module.exit_json(changed=changed, volume=instance)


def main():
    argument_spec = rax_argument_spec()
    argument_spec.update(
        dict(
            description=dict(),
            image=dict(),
            meta=dict(type='dict', default={}),
            name=dict(required=True),
            size=dict(type='int', default=100),
            snapshot_id=dict(),
            state=dict(default='present', choices=['present', 'absent']),
            volume_type=dict(choices=['SSD', 'SATA'], default='SATA'),
            wait=dict(type='bool', default=False),
            wait_timeout=dict(type='int', default=300)
        )
    )

    module = AnsibleModule(
        argument_spec=argument_spec,
        required_together=rax_required_together()
    )

    if not HAS_PYRAX:
        module.fail_json(msg='pyrax is required for this module')

    description = module.params.get('description')
    image = module.params.get('image')
    meta = module.params.get('meta')
    name = module.params.get('name')
    size = module.params.get('size')
    snapshot_id = module.params.get('snapshot_id')
    state = module.params.get('state')
    volume_type = module.params.get('volume_type')
    wait = module.params.get('wait')
    wait_timeout = module.params.get('wait_timeout')

    setup_rax_module(module, pyrax)

    cloud_block_storage(module, state, name, description, meta, size,
                        snapshot_id, volume_type, wait, wait_timeout,
                        image)

# import module snippets
from ansible.module_utils.basic import *
from ansible.module_utils.rax import *

### invoke the module
main()
