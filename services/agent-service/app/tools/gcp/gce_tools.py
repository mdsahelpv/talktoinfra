"""
Google Compute Engine (GCE) Tools

Provides tools for managing Google Compute Engine instances.
"""

from typing import Any, Dict, List, Optional
from google.cloud import compute_v1
from google.api_core.exceptions import GoogleAPIError
import structlog


logger = structlog.get_logger()


def get_gce_client(project_id: str) -> compute_v1.InstancesClient:
    """Get GCE Instances Client.

    Args:
        project_id: GCP project ID

    Returns:
        InstancesClient instance
    """
    return compute_v1.InstancesClient()


async def list_gce_instances(
    project_id: str,
    zone: Optional[str] = None,
) -> List[Dict[str, Any]]:
    """List Google Compute Engine instances.

    Args:
        project_id: GCP project ID
        zone: Optional zone to filter by (e.g., 'us-central1-a')

    Returns:
        List of instance information dictionaries
    """
    try:
        client = get_gce_client(project_id)
        
        result = []
        
        if zone:
            # List instances in specific zone
            instances = client.list(project=project_id, zone=zone)
            for instance in instances:
                result.append(_format_instance(instance))
        else:
            # List instances in all zones
            # Get list of zones first
            zones_client = compute_v1.ZonesClient()
            zones = zones_client.list(project=project_id)
            
            for zone_obj in zones:
                try:
                    instances = client.list(project=project_id, zone=zone_obj.name)
                    for instance in instances:
                        result.append(_format_instance(instance))
                except GoogleAPIError:
                    continue

        logger.info("gce_instances_listed", count=len(result), project_id=project_id)
        return result

    except GoogleAPIError as e:
        logger.error("gce_list_instances_failed", error=str(e))
        raise


async def get_gce_instance(
    project_id: str,
    zone: str,
    instance_name: str,
) -> Dict[str, Any]:
    """Get Google Compute Engine instance details.

    Args:
        project_id: GCP project ID
        zone: Zone name (e.g., 'us-central1-a')
        instance_name: Instance name

    Returns:
        Instance information dictionary
    """
    try:
        client = get_gce_client(project_id)
        instance = client.get(project=project_id, zone=zone, instance=instance_name)

        result = _format_instance(instance)
        result["zone"] = zone

        logger.info("gce_instance_retrieved", instance_name=instance_name, zone=zone)
        return result

    except GoogleAPIError as e:
        logger.error("gce_get_instance_failed", error=str(e), instance_name=instance_name)
        raise


async def start_gce_instance(
    project_id: str,
    zone: str,
    instance_name: str,
) -> Dict[str, Any]:
    """Start a Google Compute Engine instance.

    Args:
        project_id: GCP project ID
        zone: Zone name (e.g., 'us-central1-a')
        instance_name: Instance name

    Returns:
        Operation result dictionary
    """
    try:
        client = get_gce_client(project_id)
        
        # Start the instance
        operation = client.start(project=project_id, zone=zone, instance=instance_name)
        
        # Wait for operation to complete
        wait_for_operation(project_id, operation.name)
        
        result = {
            "status": "started",
            "instance_name": instance_name,
            "zone": zone,
        }

        logger.info("gce_instance_started", instance_name=instance_name, zone=zone)
        return result

    except GoogleAPIError as e:
        logger.error("gce_start_instance_failed", error=str(e), instance_name=instance_name)
        raise


async def stop_gce_instance(
    project_id: str,
    zone: str,
    instance_name: str,
) -> Dict[str, Any]:
    """Stop a Google Compute Engine instance.

    Args:
        project_id: GCP project ID
        zone: Zone name (e.g., 'us-central1-a')
        instance_name: Instance name

    Returns:
        Operation result dictionary
    """
    try:
        client = get_gce_client(project_id)
        
        # Stop the instance
        operation = client.stop(project=project_id, zone=zone, instance=instance_name)
        
        # Wait for operation to complete
        wait_for_operation(project_id, operation.name)
        
        result = {
            "status": "stopped",
            "instance_name": instance_name,
            "zone": zone,
        }

        logger.info("gce_instance_stopped", instance_name=instance_name, zone=zone)
        return result

    except GoogleAPIError as e:
        logger.error("gce_stop_instance_failed", error=str(e), instance_name=instance_name)
        raise


async def reset_gce_instance(
    project_id: str,
    zone: str,
    instance_name: str,
) -> Dict[str, Any]:
    """Reset a Google Compute Engine instance.

    Args:
        project_id: GCP project ID
        zone: Zone name (e.g., 'us-central1-a')
        instance_name: Instance name

    Returns:
        Operation result dictionary
    """
    try:
        client = get_gce_client(project_id)
        
        # Reset the instance
        operation = client.reset(project=project_id, zone=zone, instance=instance_name)
        
        # Wait for operation to complete
        wait_for_operation(project_id, operation.name)
        
        result = {
            "status": "reset",
            "instance_name": instance_name,
            "zone": zone,
        }

        logger.info("gce_instance_reset", instance_name=instance_name, zone=zone)
        return result

    except GoogleAPIError as e:
        logger.error("gce_reset_instance_failed", error=str(e), instance_name=instance_name)
        raise


async def create_gce_instance(
    project_id: str,
    zone: str,
    instance_name: str,
    machine_type: str = "e2-medium",
    image_project: str = "debian-cloud",
    image_family: str = "debian-11",
    network: str = "global/networks/default",
    startup_script: Optional[str] = None,
) -> Dict[str, Any]:
    """Create a Google Compute Engine instance.

    Args:
        project_id: GCP project ID
        zone: Zone name (e.g., 'us-central1-a')
        instance_name: Instance name
        machine_type: Machine type (e.g., 'e2-medium')
        image_project: Image project
        image_family: Image family
        network: Network name
        startup_script: Optional startup script

    Returns:
        Created instance information dictionary
    """
    try:
        client = get_gce_client(project_id)
        
        # Get machine type URL
        machine_type_url = f"projects/{project_id}/zones/{zone}/machineTypes/{machine_type}"
        
        # Get image
        images_client = compute_v1.ImagesClient()
        image = images_client.get(project=image_project, image=image_family)
        disk_init = compute_v1.AttachedDisk()
        initialize_params = compute_v1.AttachedDiskInitializeParams()
        initialize_params.source_image = image.self_link
        initialize_params.disk_size_gb = 20
        disk_init.initialize_params = initialize_params
        disk_init.auto_delete = True
        disk_init.boot = True
        
        # Build network interface
        network_interface = compute_v1.NetworkInterface()
        network_interface.network = network
        
        # Build instance config
        config = compute_v1.Instance()
        config.name = instance_name
        config.machine_type = machine_type_url
        config.disks = [disk_init]
        config.network_interfaces = [network_interface]
        
        if startup_script:
            config.metadata = compute_v1.Metadata()
            items = compute_v1.Items()
            items.key = "startup-script"
            items.value = startup_script
            config.metadata.items = [items]
        
        # Create instance
        operation = client.insert(project=project_id, zone=zone, instance_resource=config)
        
        # Wait for operation to complete
        wait_for_operation(project_id, operation.name)
        
        result = {
            "status": "created",
            "instance_name": instance_name,
            "zone": zone,
            "machine_type": machine_type,
        }

        logger.info("gce_instance_created", instance_name=instance_name, zone=zone)
        return result

    except GoogleAPIError as e:
        logger.error("gce_create_instance_failed", error=str(e), instance_name=instance_name)
        raise


async def delete_gce_instance(
    project_id: str,
    zone: str,
    instance_name: str,
) -> Dict[str, Any]:
    """Delete a Google Compute Engine instance.

    Args:
        project_id: GCP project ID
        zone: Zone name (e.g., 'us-central1-a')
        instance_name: Instance name

    Returns:
        Operation result dictionary
    """
    try:
        client = get_gce_client(project_id)
        
        # Delete instance
        operation = client.delete(project=project_id, zone=zone, instance=instance_name)
        
        # Wait for operation to complete
        wait_for_operation(project_id, operation.name)
        
        result = {
            "status": "deleted",
            "instance_name": instance_name,
            "zone": zone,
        }

        logger.info("gce_instance_deleted", instance_name=instance_name, zone=zone)
        return result

    except GoogleAPIError as e:
        logger.error("gce_delete_instance_failed", error=str(e), instance_name=instance_name)
        raise


def _format_instance(instance: compute_v1.Instance) -> Dict[str, Any]:
    """Format instance to dictionary.

    Args:
        instance: Instance resource

    Returns:
        Formatted dictionary
    """
    return {
        "id": instance.id,
        "name": instance.name,
        "machine_type": instance.machine_type.split("/")[-1],
        "status": instance.status.name if instance.status else "UNKNOWN",
        "zone": instance.zone.split("/")[-1] if instance.zone else None,
        "network": instance.network_interfaces[0].network.split("/")[-1] if instance.network_interfaces else None,
        "internal_ip": instance.network_interfaces[0].network_i_p if instance.network_interfaces else None,
        "external_ip": instance.network_interfaces[0].access_configs[0].nat_i_p if instance.network_interfaces and instance.network_interfaces[0].access_configs else None,
        "cpu_platform": instance.cpu_platform,
        "labels": dict(instance.labels) if instance.labels else {},
    }


def wait_for_operation(project_id: str, operation_name: str) -> None:
    """Wait for a GCP operation to complete.

    Args:
        project_id: GCP project ID
        operation_name: Operation name
    """
    operations_client = compute_v1.ZoneOperationsClient()
    
    # Extract zone from operation name (format: projects/{project}/zones/{zone}/operations/{id})
    parts = operation_name.split("/")
    zone_name = parts[5]
    
    while True:
        operation = operations_client.get(project=project_id, zone=zone_name, operation=operation_name)
        if operation.status == compute_v1.Operation.Status.DONE:
            if operation.error:
                raise GoogleAPIError(f"Operation failed: {operation.error}")
            break
        import time
        time.sleep(1)
