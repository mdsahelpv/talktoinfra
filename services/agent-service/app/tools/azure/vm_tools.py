"""
Azure Virtual Machine Tools

Provides tools for managing Azure Virtual Machines.
"""

from typing import Any, Dict, List, Optional
from azure.identity import DefaultAzureCredential
from azure.mgmt.compute import ComputeManagementClient
from azure.core.exceptions import AzureError
import structlog


logger = structlog.get_logger()


def get_azure_compute_client(subscription_id: str) -> ComputeManagementClient:
    """Get Azure Compute Management Client.

    Args:
        subscription_id: Azure subscription ID

    Returns:
        ComputeManagementClient instance
    """
    credential = DefaultAzureCredential()
    return ComputeManagementClient(credential, subscription_id)


async def list_azure_vms(
    subscription_id: str,
    resource_group: Optional[str] = None,
) -> List[Dict[str, Any]]:
    """List Azure Virtual Machines.

    Args:
        subscription_id: Azure subscription ID
        resource_group: Optional resource group name to filter by

    Returns:
        List of VM information dictionaries
    """
    try:
        client = get_azure_compute_client(subscription_id)
        
        if resource_group:
            vms = client.virtual_machines.list(resource_group_name=resource_group)
        else:
            # List all VMs in subscription (requires subscription-level access)
            vms = []
            for rg in client.resource_groups.list():
                try:
                    rg_vms = client.virtual_machines.list(resource_group_name=rg.name)
                    vms.extend(rg_vms)
                except AzureError:
                    continue

        result = []
        for vm in vms:
            result.append({
                "id": vm.id,
                "name": vm.name,
                "resource_group": vm.id.split("/")[4],
                "location": vm.location,
                "vm_size": vm.hardware_profile.vm_size,
                "provisioning_state": vm.provisioning_state,
                "power_state": _get_vm_power_state(vm),
                "os_type": vm.storage_profile.os_disk.os_type.value if vm.storage_profile.os_disk else None,
                "tags": vm.tags or {},
            })

        logger.info("azure_vms_listed", count=len(result), subscription_id=subscription_id)
        return result

    except AzureError as e:
        logger.error("azure_list_vms_failed", error=str(e))
        raise


async def get_azure_vm(
    subscription_id: str,
    resource_group: str,
    vm_name: str,
) -> Dict[str, Any]:
    """Get Azure Virtual Machine details.

    Args:
        subscription_id: Azure subscription ID
        resource_group: Resource group name
        vm_name: VM name

    Returns:
        VM information dictionary
    """
    try:
        client = get_azure_compute_client(subscription_id)
        vm = client.virtual_machines.get(resource_group_name=resource_group, vm_name=vm_name)

        result = {
            "id": vm.id,
            "name": vm.name,
            "resource_group": resource_group,
            "location": vm.location,
            "vm_size": vm.hardware_profile.vm_size,
            "provisioning_state": vm.provisioning_state,
            "power_state": _get_vm_power_state(vm),
            "os_type": vm.storage_profile.os_disk.os_type.value if vm.storage_profile.os_disk else None,
            "os_disk": {
                "name": vm.storage_profile.os_disk.name,
                "disk_size_gb": vm.storage_profile.os_disk.disk_size_gb,
                "storage_account_type": vm.storage_profile.os_disk.managed_disk.storage_account_type,
            } if vm.storage_profile.os_disk else None,
            "data_disks": [
                {
                    "name": disk.name,
                    "disk_size_gb": disk.disk_size_gb,
                    "lun": disk.lun,
                }
                for disk in (vm.storage_profile.data_disks or [])
            ],
            "network_interfaces": [
                nic.id.split("/")[-1] for nic in (vm.network_profile.network_interfaces or [])
            ],
            "tags": vm.tags or {},
        }

        logger.info("azure_vm_retrieved", vm_name=vm_name, resource_group=resource_group)
        return result

    except AzureError as e:
        logger.error("azure_get_vm_failed", error=str(e), vm_name=vm_name)
        raise


async def start_azure_vm(
    subscription_id: str,
    resource_group: str,
    vm_name: str,
) -> Dict[str, Any]:
    """Start an Azure Virtual Machine.

    Args:
        subscription_id: Azure subscription ID
        resource_group: Resource group name
        vm_name: VM name

    Returns:
        Operation result dictionary
    """
    try:
        client = get_azure_compute_client(subscription_id)
        
        # Start the VM
        poller = client.virtual_machines.begin_start(
            resource_group_name=resource_group,
            vm_name=vm_name
        )
        poller.wait()
        
        result = {
            "status": "started",
            "vm_name": vm_name,
            "resource_group": resource_group,
        }
        
        logger.info("azure_vm_started", vm_name=vm_name, resource_group=resource_group)
        return result

    except AzureError as e:
        logger.error("azure_start_vm_failed", error=str(e), vm_name=vm_name)
        raise


async def stop_azure_vm(
    subscription_id: str,
    resource_group: str,
    vm_name: str,
    deallocate: bool = True,
) -> Dict[str, Any]:
    """Stop an Azure Virtual Machine.

    Args:
        subscription_id: Azure subscription ID
        resource_group: Resource group name
        vm_name: VM name
        deallocate: Whether to deallocate the VM (default True)

    Returns:
        Operation result dictionary
    """
    try:
        client = get_azure_compute_client(subscription_id)
        
        if deallocate:
            poller = client.virtual_machines.begin_deallocate(
                resource_group_name=resource_group,
                vm_name=vm_name
            )
        else:
            poller = client.virtual_machines.begin_power_off(
                resource_group_name=resource_group,
                vm_name=vm_name
            )
        poller.wait()
        
        result = {
            "status": "stopped",
            "deallocated": deallocate,
            "vm_name": vm_name,
            "resource_group": resource_group,
        }
        
        logger.info("azure_vm_stopped", vm_name=vm_name, resource_group=resource_group, deallocate=deallocate)
        return result

    except AzureError as e:
        logger.error("azure_stop_vm_failed", error=str(e), vm_name=vm_name)
        raise


async def restart_azure_vm(
    subscription_id: str,
    resource_group: str,
    vm_name: str,
) -> Dict[str, Any]:
    """Restart an Azure Virtual Machine.

    Args:
        subscription_id: Azure subscription ID
        resource_group: Resource group name
        vm_name: VM name

    Returns:
        Operation result dictionary
    """
    try:
        client = get_azure_compute_client(subscription_id)
        
        poller = client.virtual_machines.begin_restart(
            resource_group_name=resource_group,
            vm_name=vm_name
        )
        poller.wait()
        
        result = {
            "status": "restarted",
            "vm_name": vm_name,
            "resource_group": resource_group,
        }
        
        logger.info("azure_vm_restarted", vm_name=vm_name, resource_group=resource_group)
        return result

    except AzureError as e:
        logger.error("azure_restart_vm_failed", error=str(e), vm_name=vm_name)
        raise


async def create_azure_vm(
    subscription_id: str,
    resource_group: str,
    vm_name: str,
    location: str,
    vm_size: str,
    admin_username: str,
    ssh_public_key: Optional[str] = None,
    password: Optional[str] = None,
    image: Optional[Dict[str, str]] = None,
) -> Dict[str, Any]:
    """Create an Azure Virtual Machine.

    Args:
        subscription_id: Azure subscription ID
        resource_group: Resource group name
        vm_name: VM name
        location: Azure region
        vm_size: VM size (e.g., 'Standard_DS1_v2')
        admin_username: Admin username
        ssh_public_key: Optional SSH public key
        password: Optional admin password
        image: Optional image reference (publisher, offer, sku, version)

    Returns:
        Created VM information dictionary
    """
    try:
        client = get_azure_compute_client(subscription_id)
        
        # Build OS profile
        if ssh_public_key:
            os_profile = {
                "admin_username": admin_username,
                "linux_configuration": {
                    "ssh": {
                        "public_keys": [
                            {
                                "key_data": ssh_public_key,
                                "path": f"/home/{admin_username}/.ssh/authorized_keys"
                            }
                        ]
                    }
                }
            }
        elif password:
            os_profile = {
                "admin_username": admin_username,
                "admin_password": password,
            }
        else:
            raise ValueError("Either ssh_public_key or password must be provided")
        
        # Build image reference
        if image:
            image_ref = {
                "publisher": image.get("publisher", "Canonical"),
                "offer": image.get("offer", "UbuntuServer"),
                "sku": image.get("sku", "18.04-LTS"),
                "version": image.get("version", "latest"),
            }
        else:
            image_ref = {
                "publisher": "Canonical",
                "offer": "UbuntuServer",
                "sku": "18.04-LTS",
                "version": "latest",
            }
        
        # Create VM parameters
        vm_params = {
            "location": location,
            "hardware_profile": {
                "vm_size": vm_size,
            },
            "storage_profile": {
                "image_reference": image_ref,
                "os_disk": {
                    "name": f"{vm_name}-osdisk",
                    "disk_size_gb": 30,
                    "managed_disk": {
                        "storage_account_type": "Standard_LRS",
                    },
                },
            },
            "os_profile": os_profile,
            "network_profile": {
                "network_interfaces": [
                    {
                        "id": f"/subscriptions/{subscription_id}/resourceGroups/{resource_group}/providers/Microsoft.Network/networkInterfaces/{vm_name}-nic",
                    }
                ]
            },
        }
        
        poller = client.virtual_machines.begin_create_or_update(
            resource_group_name=resource_group,
            vm_name=vm_name,
            parameters=vm_params,
        )
        vm = poller.result()
        
        result = {
            "status": "created",
            "vm_name": vm.name,
            "resource_group": resource_group,
            "location": vm.location,
            "vm_size": vm.hardware_profile.vm_size,
        }
        
        logger.info("azure_vm_created", vm_name=vm_name, resource_group=resource_group)
        return result

    except AzureError as e:
        logger.error("azure_create_vm_failed", error=str(e), vm_name=vm_name)
        raise


async def delete_azure_vm(
    subscription_id: str,
    resource_group: str,
    vm_name: str,
) -> Dict[str, Any]:
    """Delete an Azure Virtual Machine.

    Args:
        subscription_id: Azure subscription ID
        resource_group: Resource group name
        vm_name: VM name

    Returns:
        Operation result dictionary
    """
    try:
        client = get_azure_compute_client(subscription_id)
        
        poller = client.virtual_machines.begin_delete(
            resource_group_name=resource_group,
            vm_name=vm_name
        )
        poller.wait()
        
        result = {
            "status": "deleted",
            "vm_name": vm_name,
            "resource_group": resource_group,
        }
        
        logger.info("azure_vm_deleted", vm_name=vm_name, resource_group=resource_group)
        return result

    except AzureError as e:
        logger.error("azure_delete_vm_failed", error=str(e), vm_name=vm_name)
        raise


def _get_vm_power_state(vm: Any) -> str:
    """Get VM power state from instance view.

    Args:
        vm: VirtualMachine instance

    Returns:
        Power state string
    """
    if not vm.instance_view:
        return "Unknown"
    
    for status in (vm.instance_view.statuses or []):
        if status.code.startswith("PowerState/"):
            return status.code.split("/")[-1]
    
    return "Unknown"
