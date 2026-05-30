"""Active Directory action executor."""

import asyncio


async def execute_ad_action(action: str, params: dict) -> dict:
    try:
        commands = {
            "ad_search_user": f"powershell Get-ADUser -Filter 'SamAccountName -eq \"{params['username']}\"' -Properties * | ConvertTo-Json",
            "ad_user_status": f"powershell Get-ADUser -Identity {params['username']} -Properties Enabled,LockedOut,LastLogonDate,PasswordLastSet,AccountExpirationDate | ConvertTo-Json",
            "ad_unlock_account": f"powershell Unlock-ADAccount -Identity {params['username']}",
            "ad_list_computers": _build_list_computers_cmd(params),
        }
        cmd = commands.get(action)
        if not cmd:
            return {"success": False, "error": f"Unknown AD action: {action}"}

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


def _build_list_computers_cmd(params: dict) -> str:
    base = params.get("search_base", "")
    if base:
        return f"powershell Get-ADComputer -SearchBase '{base}' -Properties OperatingSystem,LastLogonDate | ConvertTo-Json"
    return "powershell Get-ADComputer -Properties OperatingSystem,LastLogonDate | ConvertTo-Json | Select-Object -First 50"
