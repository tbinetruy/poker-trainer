import json

from channels.generic.websocket import AsyncJsonWebsocketConsumer

from apps.tables.selectors import get_game_snapshot_async


class TableConsumer(AsyncJsonWebsocketConsumer):
    async def connect(self) -> None:
        self.game_id = self.scope["url_route"]["kwargs"]["game_id"]
        self.group_name = f"table-{self.game_id}"
        snapshot = await get_game_snapshot_async(self.game_id)

        if snapshot is None:
            await self.close(code=4404)
            return

        await self.channel_layer.group_add(self.group_name, self.channel_name)
        await self.accept()
        await self.send_json(
            {
                "type": "table.snapshot",
                "payload": snapshot,
            }
        )

    async def disconnect(self, close_code: int) -> None:
        await self.channel_layer.group_discard(self.group_name, self.channel_name)

    async def receive_json(self, content: dict, **kwargs: object) -> None:
        if content.get("type") == "ping":
            await self.send_json({"type": "pong"})
            return

        await self.send_json(
            {
                "type": "error",
                "payload": {"message": "Milestone 1 only supports table snapshots."},
            }
        )

    async def table_snapshot(self, event: dict) -> None:
        await self.send_json({"type": "table.snapshot", "payload": event["payload"]})

    async def table_thinking(self, event: dict) -> None:
        await self.send_json({"type": "table.thinking", "payload": event["payload"]})

    async def decode_json(self, text_data: str) -> dict:
        return json.loads(text_data)
