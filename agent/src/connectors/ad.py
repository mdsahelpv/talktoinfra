"""Active Directory connector using ldap3."""

from ldap3 import Server, Connection, ALL, core

from src.connectors.base import BaseConnector
from src.config import AgentConfig


class ADConnector(BaseConnector):
    def __init__(self, cfg: AgentConfig):
        self._cfg = cfg
        self._available = False
        self._conn: Connection | None = None

    async def initialize(self) -> None:
        if not self._cfg.ad_server:
            self._available = False
            return
        try:
            server = Server(self._cfg.ad_server, get_info=ALL)
            self._conn = Connection(
                server,
                user=f"{self._cfg.ad_username}@{self._cfg.ad_domain}",
                password=self._cfg.ad_password,
                auto_bind=True,
            )
            self._available = True
        except Exception as e:
            print(f"[ad] Init failed: {e}")
            self._available = False

    @property
    def name(self) -> str:
        return "active_directory"

    @property
    def is_available(self) -> bool:
        return self._available

    async def health(self) -> dict:
        if not self._available or not self._conn:
            return {"healthy": False, "error": "Not connected"}
        return {"healthy": self._conn.bound}

    async def execute(self, action: str, params: dict) -> dict:
        handlers = {
            "ad_search_user": self._search_user,
            "ad_user_status": self._user_status,
            "ad_unlock_account": self._unlock_account,
            "ad_list_computers": self._list_computers,
        }
        handler = handlers.get(action)
        if not handler:
            return {"success": False, "error": f"Unknown AD action: {action}"}
        return await handler(params)

    async def _search_user(self, params: dict) -> dict:
        username = params["username"]
        search_base = self._get_default_base()
        self._conn.search(
            search_base=search_base,
            search_filter=f"(sAMAccountName={username})",
            attributes=["cn", "displayName", "mail", "department", "title", "memberOf"],
        )
        entries = []
        for e in self._conn.entries:
            entries.append({
                "dn": str(e.entry_dn),
                "cn": str(e.cn) if hasattr(e, "cn") else "",
                "display_name": str(e.displayName) if hasattr(e, "displayName") else "",
                "email": str(e.mail) if hasattr(e, "mail") else "",
                "department": str(e.department) if hasattr(e, "department") else "",
                "groups": [str(g) for g in (e.memberOf or [])],
            })
        return {"success": True, "output": entries}

    async def _user_status(self, params: dict) -> dict:
        username = params["username"]
        search_base = self._get_default_base()
        self._conn.search(
            search_base=search_base,
            search_filter=f"(sAMAccountName={username})",
            attributes=["cn", "userAccountControl", "lastLogon", "pwdLastSet", "accountExpires"],
        )
        for e in self._conn.entries:
            uac = int(e.userAccountControl) if hasattr(e, "userAccountControl") else 0
            return {"success": True, "output": {
                "username": username,
                "enabled": not (uac & 2),
                "locked": bool(uac & 16),
                "password_expired": bool(uac & 8388608),
            }}
        return {"success": False, "error": f"User {username} not found"}

    async def _unlock_account(self, params: dict) -> dict:
        username = params["username"]
        search_base = self._get_default_base()
        self._conn.search(search_base, f"(sAMAccountName={username})", attributes=["distinguishedName"])
        for e in self._conn.entries:
            dn = str(e.entry_dn)
            self._conn.modify(dn, {"lockoutTime": [(2, "0")]})
            return {"success": True, "output": f"Unlocked account {username}"}
        return {"success": False, "error": f"User {username} not found"}

    async def _list_computers(self, params: dict) -> dict:
        search_base = params.get("search_base") or self._get_default_base()
        self._conn.search(
            search_base=search_base,
            search_filter="(objectClass=computer)",
            attributes=["cn", "operatingSystem", "lastLogonDate"],
        )
        items = []
        for e in self._conn.entries:
            items.append({
                "name": str(e.cn) if hasattr(e, "cn") else "",
                "os": str(e.operatingSystem) if hasattr(e, "operatingSystem") else "",
                "last_logon": str(e.lastLogonDate) if hasattr(e, "lastLogonDate") else "",
            })
        return {"success": True, "output": items}

    def _get_default_base(self) -> str:
        parts = self._cfg.ad_domain.split(".")
        return ",".join(f"DC={p}" for p in parts)
