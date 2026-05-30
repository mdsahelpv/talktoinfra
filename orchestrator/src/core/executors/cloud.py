"""Cloud action executor — AWS, Azure, GCP."""

import asyncio


async def execute_cloud_action(action: str, params: dict) -> dict:
    try:
        region = params.get("region", "")
        region_flag = f"--region {region}" if region else ""

        commands = {
            "aws_list_ec2": f"aws ec2 describe-instances {region_flag} --query 'Reservations[].Instances[].[InstanceId,State.Name,InstanceType,Tags[?Key==`Name`].Value|[0]]' --output json",
            "aws_describe_vpc": f"aws ec2 describe-vpcs {region_flag} --output json",
            "aws_start_instance": f"aws ec2 start-instances --instance-ids {params['instance_id']} {region_flag}",
            "aws_stop_instance": f"aws ec2 stop-instances --instance-ids {params['instance_id']} {region_flag}",
        }

        cmd = commands.get(action)
        if not cmd:
            return {"success": False, "error": f"Unknown cloud action: {action}"}

        proc = await asyncio.create_subprocess_shell(
            cmd, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE
        )
        stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=30)
        if proc.returncode != 0:
            return {"success": False, "error": stderr.decode().strip()}
        return {"success": True, "output": stdout.decode().strip()}
    except asyncio.TimeoutError:
        return {"success": False, "error": "Command timed out"}
    except Exception as e:
        return {"success": False, "error": str(e)}
