# Some useful information and other stuff

## Run this command to execute the playbook:

    [drusso@dom-ryzen CNIT499]$ ansible-playbook -i inventory/hosts -K kvm_provision.yml
    

## Import an ssh-rsa key on IOSXRv

Convert rsa key to Base64:

    [drusso@dom-ryzen .ssh]$ cat mykey.pub | cut -f 2 -d ' ' | base64 -D > mykey.bin

Import Base64 key from a TFTP server:
        
    RP/0/0/CPU0:iosxr-3#crypto key import authentication rsa tftp://172.24.11.10;Mgmt-vrf/ansible.bin

I don't think this does proper user authenticaton but it seems to work
Credit: https://www.ispcolohost.com/2018/01/06/key-based-ssh-authentication-to-ios-xr-devices/