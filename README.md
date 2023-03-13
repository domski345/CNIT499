# CNIT499 Independent study automation tools
This repository contains all of the tools used to create a lab enviornment on KVM. The information below is purely for our own reference.

Once netbox is up and running, assign the following device status to VMs as necessary:

- planned- create the VM
- failed- recreate the VM
- decommissioning- delete the VM

Don't set the status to anything else, VMs currently in use will be set to **active** once teh script creates them.

## Run this command to execute the playbook:

    [drusso@dom-ryzen CNIT499]$ ansible-playbook -i inventory/hosts -K kvm_provision.yml
    
## Import an ssh-rsa key on IOSXRv

Convert rsa key to Base64:

    [drusso@dom-ryzen .ssh]$ cat mykey.pub | cut -f 2 -d ' ' | base64 -D > mykey.bin

Import Base64 key from a TFTP server:
        
    RP/0/0/CPU0:iosxr-3#crypto key import authentication rsa tftp://172.24.11.10;Mgmt-vrf/ansible.bin

I don't think this does proper user authenticaton but it seems to work(AAA is beyond the scope of this study).
(Credit: https://www.ispcolohost.com/2018/01/06/key-based-ssh-authentication-to-ios-xr-devices/)

## Set permissions for GlusterFS

    gluster volume set gv0 group virt
    gluster volume set gv0 storage.owner-uid 36
    
Thanks: https://zenteric.com/2017/02/how-to-add-glusterfs-to-ovirt-rhev/