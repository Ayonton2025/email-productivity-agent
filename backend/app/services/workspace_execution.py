"""Persist confirmed workspace drafts using the existing transaction boundaries."""

from fastapi import HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import logger
from app.models.agent_models import Agent
from app.models.campaign_models import Campaign, CampaignSequence, Lead
from app.models.prompt_models import PromptTemplate
from app.models.user_models import User
from app.models.workflow_models import Workflow, WorkflowStep


async def _execute_assistant_draft(
    page: str, draft: dict, objective: str, current_user: User, session: AsyncSession
) -> dict:
    """Execute structured AI draft by creating entities directly."""
    page_key = (page or "").strip().lower()

    try:
        if page_key == "campaigns":
            campaign_payload = draft.get("campaign", {}) if isinstance(draft, dict) else {}
            name = campaign_payload.get("name") or f"AI Campaign - {objective[:40]}"
            from_email = campaign_payload.get("from_email") or getattr(current_user, "email", None)
            if not from_email:
                raise HTTPException(status_code=400, detail="Campaign execution requires from_email")

            campaign = Campaign(
                user_id=current_user.id,
                name=name,
                description=campaign_payload.get("description"),
                campaign_type=campaign_payload.get("campaign_type", "cold_outreach"),
                from_email=from_email,
                from_name=campaign_payload.get("from_name"),
                reply_to=campaign_payload.get("reply_to"),
                daily_send_limit=campaign_payload.get("daily_send_limit", 50),
                send_delay_minutes=campaign_payload.get("send_delay_minutes", 5),
                timezone=campaign_payload.get("timezone", "UTC"),
                send_hours=campaign_payload.get("send_hours", []),
                warm_up_enabled=campaign_payload.get("warm_up_enabled", False),
                warm_up_emails_per_day=campaign_payload.get("warm_up_emails_per_day", 5),
                ab_test_enabled=campaign_payload.get("ab_test_enabled", False),
                ab_test_split=campaign_payload.get("ab_test_split", 0.5),
                tags=campaign_payload.get("tags", []),
                status="draft",
            )
            session.add(campaign)
            await session.flush()

            created_sequences = 0
            for idx, seq in enumerate(draft.get("sequences", []) if isinstance(draft, dict) else [], start=1):
                if not seq.get("subject_template") or not seq.get("body_template"):
                    continue
                sequence = CampaignSequence(
                    campaign_id=campaign.id,
                    step_order=idx,
                    name=seq.get("name") or f"Step {idx}",
                    subject_template=seq.get("subject_template"),
                    body_template=seq.get("body_template"),
                    delay_days=seq.get("delay_days", 0),
                    delay_hours=seq.get("delay_hours", 0),
                    send_if_opened=seq.get("send_if_opened", False),
                    send_if_clicked=seq.get("send_if_clicked", False),
                    send_if_replied=seq.get("send_if_replied", False),
                    stop_if_replied=seq.get("stop_if_replied", True),
                )
                session.add(sequence)
                created_sequences += 1

            created_leads = 0
            for lead in draft.get("leads", []) if isinstance(draft, dict) else []:
                email = lead.get("email")
                if not email:
                    continue
                lead_record = Lead(
                    campaign_id=campaign.id,
                    user_id=current_user.id,
                    email=email,
                    first_name=lead.get("first_name"),
                    last_name=lead.get("last_name"),
                    company=lead.get("company"),
                    job_title=lead.get("job_title"),
                    custom_fields=lead.get("custom_fields", {}),
                )
                session.add(lead_record)
                created_leads += 1

            await session.commit()
            await session.refresh(campaign)
            return {
                "mode": "execute",
                "page": "campaigns",
                "created": {"campaign_id": campaign.id, "sequences": created_sequences, "leads": created_leads},
            }

        if page_key == "workflows":
            workflow_payload = draft.get("workflow", {}) if isinstance(draft, dict) else {}
            workflow = Workflow(
                user_id=current_user.id,
                name=workflow_payload.get("name") or f"AI Workflow - {objective[:40]}",
                description=workflow_payload.get("description"),
                trigger_type=workflow_payload.get("trigger_type", "email_received"),
                trigger_conditions=workflow_payload.get("trigger_conditions", {}),
                run_on_match=workflow_payload.get("run_on_match", True),
                require_approval=workflow_payload.get("require_approval", False),
                tags=workflow_payload.get("tags", []),
            )
            session.add(workflow)
            await session.flush()

            created_steps = 0
            for idx, step in enumerate(draft.get("steps", []) if isinstance(draft, dict) else [], start=1):
                step_record = WorkflowStep(
                    workflow_id=workflow.id,
                    step_order=idx,
                    name=step.get("name") or f"Step {idx}",
                    step_type=step.get("step_type", "action"),
                    action_type=step.get("action_type"),
                    action_config=step.get("action_config", {}),
                    condition_type=step.get("condition_type"),
                    condition_config=step.get("condition_config", {}),
                    delay_seconds=step.get("delay_seconds"),
                    on_error=step.get("on_error", "stop"),
                    max_retries=step.get("max_retries", 0),
                )
                session.add(step_record)
                created_steps += 1

            await session.commit()
            await session.refresh(workflow)
            return {
                "mode": "execute",
                "page": "workflows",
                "created": {"workflow_id": workflow.id, "steps": created_steps},
            }

        if page_key == "agents":
            agent_payload = draft.get("agent", {}) if isinstance(draft, dict) else {}
            system_prompt = agent_payload.get("system_prompt") or "You are a helpful email assistant."
            agent = Agent(
                user_id=current_user.id,
                name=agent_payload.get("name") or f"AI Agent - {objective[:40]}",
                agent_type=agent_payload.get("agent_type", "support"),
                description=agent_payload.get("description"),
                system_prompt=system_prompt,
                instructions=agent_payload.get("instructions"),
                capabilities=agent_payload.get("capabilities", []),
                subscribe_to_categories=agent_payload.get("subscribe_to_categories", []),
                subscribe_to_senders=agent_payload.get("subscribe_to_senders", []),
                subscribe_to_keywords=agent_payload.get("subscribe_to_keywords", []),
                auto_draft_replies=agent_payload.get("auto_draft_replies", False),
                require_approval=agent_payload.get("require_approval", True),
                escalation_rules=agent_payload.get("escalation_rules", {}),
                memory_enabled=agent_payload.get("memory_enabled", True),
                context_window=agent_payload.get("context_window", 10),
                tags=agent_payload.get("tags", []),
            )
            session.add(agent)
            await session.commit()
            await session.refresh(agent)
            return {"mode": "execute", "page": "agents", "created": {"agent_id": agent.id}}

        if page_key in {"prompts", "prompt_brain"}:
            prompt_payload = draft.get("prompt", {}) if isinstance(draft, dict) else {}
            template = prompt_payload.get("template")
            if not template:
                raise HTTPException(status_code=400, detail="Prompt execution requires a template")

            prompt = PromptTemplate(
                user_id=current_user.id,
                name=prompt_payload.get("name") or f"AI Prompt - {objective[:32]}",
                description=prompt_payload.get("description"),
                template=template,
                category=prompt_payload.get("category", "analysis"),
                is_active=prompt_payload.get("is_active", True),
                is_system=False,
            )
            session.add(prompt)
            await session.commit()
            await session.refresh(prompt)
            return {"mode": "execute", "page": "prompts", "created": {"prompt_id": prompt.id}}

        return {
            "mode": "execute",
            "page": page_key or "unknown",
            "created": {},
            "message": "No execution handler is available for this page.",
        }
    except HTTPException:
        await session.rollback()
        raise
    except Exception as e:
        await session.rollback()
        logger.error(f"Assistant execute failed ({page_key}): {e}")
        raise HTTPException(status_code=500, detail=f"Assistant execute failed for {page_key}")
