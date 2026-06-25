import sys; sys.path.insert(0,'.')
import asyncio, json
from sqlalchemy import select
from app.db.session import AsyncSessionLocal
from app.models.models import User, Task
from app.api.v1.ai import _DEDUPE_SYSTEM
from app.services.ai_service import client as _client, MODEL as _MODEL

async def test():
    async with AsyncSessionLocal() as db:
        user = (await db.execute(select(User).where(User.email == 'anayna.singh@prospect33.com'))).scalar_one()
        assigned = select(Task.project_id).where(Task.assigned_to == user.id).scalar_subquery()
        res = await db.execute(select(Task).where(Task.is_completed == False, Task.status != 'cancelled', Task.project_id.in_(assigned)).limit(30))
        existing = res.scalars().all()

        existing_list = '\n'.join([f'- [{t.id}] "{t.title}" | {t.status.value}' for t in existing])
        proposed = '- "Make the to do list app mobile responsive"'

        resp = await _client.chat.completions.create(
            model=_MODEL,
            messages=[{'role':'system','content':_DEDUPE_SYSTEM},{'role':'user','content':f'EXISTING:\n{existing_list}\n\nPROPOSED:\n{proposed}'}],
            response_format={'type':'json_object'},
            temperature=0.1,
        )
        matches = json.loads(resp.choices[0].message.content)
        matches = matches.get('matches', matches) if isinstance(matches, dict) else matches
        for m in matches:
            conf = round(float(m.get('confidence', 0)) * 100)
            print(f'[{m["match_type"].upper()}] Confidence: {conf}%')
            print(f'  Proposed:  "{m["proposed_title"]}"')
            if m.get('existing_task_title'):
                print(f'  Matches:   "{m["existing_task_title"]}" [{m.get("existing_task_status")}]')
            print(f'  Action:    {m["suggested_action"]}')
            print(f'  Reason:    {m["suggestion"]}')

asyncio.run(test())
